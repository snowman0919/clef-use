"""Owned, recoverable deployment of instruction-only Agent Skills and MCP entries."""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from contextlib import ExitStack, contextmanager
from pathlib import Path, PureWindowsPath

import tomlkit
from filelock import FileLock
from packaging.specifiers import SpecifierSet
from ruamel.yaml.error import YAMLError

from .harness import (
    atomic_write,
    install_mcp,
    omp_profile,
    read_config,
    render_entry,
    server_entry,
    target_path,
)

HARNESSES = ("codex", "hermes", "omp")
SKILLS = {"core": "clef-use", "blender": "clef-use-blender", "diagnostics": "clef-use-diagnostics"}


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe(path: Path) -> None:
    """Reject links in every existing ancestor, including dangling links."""
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f"symlink is not a managed installation target: {part}")


def _layout(harness: str, scope: str = "user", project: Path | str | None = None) -> dict:
    if harness not in HARNESSES:
        raise ValueError("harness must be codex, hermes or omp")
    if scope not in ("user", "project"):
        raise ValueError("scope must be user or project")
    home = Path.home()
    config = target_path(harness)
    profile = omp_profile() or "default" if harness == "omp" else "default"
    if harness == "hermes":
        profile = os.environ.get("HERMES_PROFILE", "default")
        if profile != "default" and not os.environ.get("HERMES_HOME"):
            raise ValueError("named Hermes profile requires explicit HERMES_HOME from the harness")
        sticky = home / ".hermes" / "active_profile"
        if not os.environ.get("HERMES_HOME") and sticky.exists():
            active = sticky.read_text().strip()
            if active not in ("", "default"):
                raise ValueError(
                    "active Hermes profile requires explicit HERMES_HOME from the harness"
                )
    elif harness == "codex":
        profile = os.environ.get("CODEX_PROFILE", "default")
        if profile != "default":
            raise ValueError(
                "Codex named profile requires explicit config selection; default not modified"
            )
    if scope == "project":
        if harness == "hermes":
            return {
                "status": "UNSUPPORTED_SCOPE",
                "reason": "use an explicit Hermes home/profile with user scope",
            }
        project = Path(project or Path.cwd()).absolute()
        if not project.is_dir():
            raise ValueError("project directory does not exist")
        root = project / (".agents" if harness == "codex" else ".omp") / "skills"
        config = project / (".codex/config.toml" if harness == "codex" else ".omp/mcp.json")
        state = project / ".clef-use" / "integrations" / harness
    else:
        root = home / ".agents/skills" if harness == "codex" else config.parent / "skills"
        if harness == "omp":
            settings = _omp_settings(config.parent)
            if (settings.get("skills") or {}).get("enableAgentsUser", True):
                root = home / ".agents/skills"
        state = config.parent / "clef-use-integrations"
        recorded = state / "manifest.json"
        if harness == "omp" and recorded.exists():
            _safe(recorded)
            saved_root = Path(json.loads(recorded.read_text()).get("root", ""))
            if saved_root not in (home / ".agents/skills", config.parent / "skills"):
                raise ValueError("managed OMP source is outside supported roots")
            root = saved_root
    registry = (
        root.parent / "clef-use-integrations.json" if root == home / ".agents/skills" else None
    )
    for path in (config, root, state):
        _safe(path)
    return {
        "harness": harness,
        "profile": profile,
        "scope": scope,
        "config": config,
        "root": root,
        "state": state,
        "project": str(project) if project else None,
        "registry": registry,
    }


def _omp_settings(directory: Path) -> dict:
    for suffix in ("config.yml", "config.yaml"):
        path = directory / suffix
        if path.is_file():
            _safe(path)
            return read_config("hermes", path.read_text())
    return {}


@contextmanager
def _locked(layout: dict):
    with ExitStack() as stack:
        registry = layout.get("registry")
        if registry:
            _safe(registry)
            registry.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            stack.enter_context(FileLock(str(registry.with_suffix(".lock"))))
        layout["state"].mkdir(parents=True, exist_ok=True, mode=0o700)
        stack.enter_context(FileLock(str(layout["state"] / "lock")))
        yield


def _registry(layout: dict) -> dict:
    path = layout.get("registry")
    raw = _read(path) if path else None
    if raw is None:
        return {
            "format": 1,
            "root": str(layout["root"]),
            "realpath": str(layout["root"].resolve()),
            "skills": {},
        }
    data = json.loads(raw)
    if data.get("root") != str(layout["root"]) or data.get("realpath") != str(
        layout["root"].resolve()
    ):
        raise ValueError("shared guide ownership root differs")
    for name, item in data.get("skills", {}).items():
        if name not in SKILLS.values() or not isinstance(item.get("owners"), list):
            raise ValueError("invalid shared guide ownership")
        for relative in item.get("files", {}):
            part = Path(relative)
            if part.is_absolute() or ".." in part.parts:
                raise ValueError("invalid shared guide file")
    return data


def _owner(layout: dict) -> str:
    return str(layout["state"] / "manifest.json")


def _managed_hashes(layout: dict, manifest: dict, name: str, registry: dict | None = None):
    if layout.get("registry"):
        registered = (registry or _registry(layout))["skills"].get(name)
        if registered and _owner(layout) in registered["owners"]:
            return registered["files"]
    return manifest.get("skills", {}).get(name, {}).get("files")


def _release_guide(layout: dict, registry: dict, name: str) -> bool:
    """Return whether this is the last approved owner of the shared guide."""
    if not layout.get("registry"):
        return True
    item = registry["skills"].get(name)
    if item is None:
        return True
    item["owners"] = [owner for owner in item["owners"] if owner != _owner(layout)]
    if item["owners"]:
        return False
    del registry["skills"][name]
    return True


def _read(path: Path) -> bytes | None:
    _safe(path)
    return path.read_bytes() if path.exists() else None


def _files(root: Path) -> dict[str, bytes]:
    _safe(root)
    if not root.exists():
        return {}
    if not root.is_dir():
        raise ValueError(f"skill target is not a directory: {root}")
    result = {}
    for path in root.rglob("*"):
        _safe(path)
        if path.is_file():
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def _digests(files: dict[str, bytes]) -> dict[str, str]:
    return {name: _hash(data) for name, data in sorted(files.items())}


def _load_manifest(layout: dict) -> dict:
    path = layout["state"] / "manifest.json"
    raw = _read(path)
    if raw is None:
        return {}
    data = json.loads(raw)
    for key in ("harness", "profile", "scope"):
        if data.get(key) != layout[key]:
            raise ValueError(f"manifest {key} differs from selected integration")
    if data.get("root") != str(layout["root"]) or data.get("config") != str(layout["config"]):
        raise ValueError("manifest target differs from selected integration")
    # Never trust arbitrary paths from a manifest, even one located under the user's HOME.
    for name, item in data.get("skills", {}).items():
        target = layout["root"] / name
        if name not in SKILLS.values() or item.get("path") != str(target):
            raise ValueError("invalid managed skill target")
        if item.get("realpath") != str(target.resolve()):
            raise ValueError("managed skill realpath changed")
        for relative in item.get("files", {}):
            part = Path(relative)
            if part.is_absolute() or ".." in part.parts:
                raise ValueError("invalid managed skill file")
    return data


def _codex_disabled_paths(data: dict) -> set[Path]:
    return {
        Path(item["path"]).expanduser().resolve()
        for item in data.get("skills", {}).get("config", [])
        if item.get("enabled") is False and item.get("path")
    }


def _disabled(layout: dict, original: str, names: list[str]) -> list[str]:
    data = read_config(layout["harness"], original)
    disabled = []
    if layout["harness"] == "codex":
        paths = _codex_disabled_paths(data)
        disabled = [
            name for name in names if (layout["root"] / name / "SKILL.md").resolve() in paths
        ]
    elif layout["harness"] == "hermes":
        skills = data.get("skills", {}) or {}
        blocked = set(skills.get("disabled", []))
        for values in (skills.get("platform_disabled", {}) or {}).values():
            blocked.update(values)
        disabled = [name for name in names if name in blocked]
    else:
        settings = _omp_settings(layout["config"].parent)
        if settings:
            if (settings.get("skills") or {}).get("enabled") is False:
                disabled = names[:]
            source = (
                "enableAgentsUser"
                if layout.get("registry")
                else ("enablePiProject" if layout["scope"] == "project" else "enablePiUser")
            )
            if (settings.get("skills") or {}).get(source) is False:
                disabled = names[:]
            blocked = settings.get("disabledExtensions", [])
            disabled += [name for name in names if f"skill:{name}" in blocked]
    return sorted(set(disabled))


def _hermes_sources(layout: dict, original: str, cwd: Path) -> list[Path]:
    settings = read_config("hermes", original).get("skills") or {}

    def entries(raw):
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list):
            return []
        return [str(item).strip() for item in raw if str(item).strip()]

    candidates = []
    create = settings.get("create_dir")
    external = entries(settings.get("external_dirs"))
    if isinstance(create, str) and create.strip():
        external.insert(0, create.strip())
    for entry in external:
        path = Path(os.path.expandvars(entry)).expanduser()
        path = (path if path.is_absolute() else layout["config"].parent / path).resolve()
        if path.is_dir():
            candidates.append(path)
    if settings.get("project_discovery") is not False:
        trusted = {
            Path(os.path.expandvars(entry)).expanduser().resolve()
            for entry in entries(settings.get("trusted_project_dirs"))
        }
        project = layout.get("project")
        if project is None:
            terminal = os.environ.get("TERMINAL_CWD", "").strip()
            configured = Path(terminal).expanduser() if terminal else None
            project = configured if configured is not None and configured.is_dir() else cwd
        project = Path(project).resolve()
        for _ in range(64):
            if (project / ".git").exists():
                if project != Path.home().resolve() and project in trusted:
                    candidates.extend(
                        project / source / "skills" for source in (".hermes", ".agents")
                    )
                break
            if project.parent == project:
                break
            project = project.parent
    return candidates


def _shadowed(layout: dict, names: list[str], original: str) -> list[dict]:
    cwd = Path(layout.get("project") or Path.cwd())
    candidates = [layout["root"]]
    if layout["harness"] == "codex" and layout["scope"] == "user":
        candidates.append(cwd / ".agents/skills")
    elif layout["harness"] == "hermes":
        candidates.extend(_hermes_sources(layout, original, cwd))
    elif layout["harness"] == "omp":
        settings = _omp_settings(layout["config"].parent).get("skills") or {}
        if settings.get("enableAgentsUser", True):
            candidates.append(Path.home() / ".agents/skills")
        if settings.get("enablePiUser", True):
            candidates.append(target_path("omp").parent / "skills")
        if settings.get("enableAgentsProject", True):
            candidates.append(cwd / ".agents/skills")
        if settings.get("enablePiProject", True):
            candidates.append(cwd / ".omp/skills")
    result = []
    hermes = layout["harness"] == "hermes"
    disabled_paths = (
        _codex_disabled_paths(read_config("codex", original))
        if layout["harness"] == "codex"
        else set()
    )
    excluded = {
        ".git",
        ".github",
        ".hub",
        ".archive",
        ".curator_backups",
        ".locks",
        ".venv",
        "venv",
        "node_modules",
        "site-packages",
        "__pycache__",
        ".tox",
        ".nox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
    support = {"references", "templates", "assets", "scripts"}
    flat_names = {name + ".md" for name in names}
    scanned = set()
    for root in candidates:
        if root.resolve() in scanned:
            continue
        scanned.add(root.resolve())
        if hermes:
            # Native explicit lookup of legacy Markdown has separate exclusions
            # from the SKILL.md catalog, including files in archived directories.
            for path in root.rglob("*.md"):
                if path.name not in flat_names or not path.is_file():
                    continue
                relative = path.relative_to(root)
                packaged = any(
                    (root.joinpath(*relative.parts[:depth]) / "SKILL.md").is_file()
                    for depth in range(1, len(relative.parts))
                )
                supporting = any(
                    parent.name in support and (parent.parent / "SKILL.md").exists()
                    for parent in path.parents
                )
                if not packaged and not supporting:
                    result.append(
                        {"name": path.stem, "path": str(path), "realpath": str(path.resolve())}
                    )
        visited = set()
        for directory, children, files in os.walk(root, followlinks=True):
            parent = Path(directory)
            resolved = parent.resolve()
            if resolved in visited:
                children[:] = []
                continue
            visited.add(resolved)
            if hermes:
                children[:] = [
                    child
                    for child in children
                    if child not in excluded and not ("SKILL.md" in files and child in support)
                ]
            children.sort()
            if "SKILL.md" not in files:
                continue
            path = parent / "SKILL.md"
            if path.resolve() in disabled_paths:
                continue
            name = parent.name
            try:
                with path.open(encoding="utf-8-sig") as stream:
                    if stream.readline().strip() == "---":
                        header = []
                        for line in stream:
                            if line.strip() in ("---", "..."):
                                try:
                                    metadata = read_config("hermes", "".join(header))
                                    if isinstance(metadata, dict):
                                        name = metadata.get("name", name)
                                except YAMLError:
                                    if hermes:
                                        for entry in header:
                                            key, separator, value = entry.partition(":")
                                            if separator and key.strip() == "name":
                                                name = value.strip()
                                break
                            header.append(line)
            except (OSError, UnicodeError) as error:
                result.append(
                    {
                        "name": None,
                        "path": str(path),
                        "realpath": str(path.resolve()),
                        "error": "skill metadata unreadable",
                        "error_type": type(error).__name__,
                    }
                )
                continue
            aliases = [parent.name, name] if hermes else [name]
            for alias in names:
                if alias in aliases and resolved != (layout["root"] / alias).resolve():
                    result.append(
                        {"name": alias, "path": str(path), "realpath": str(path.resolve())}
                    )
    return result


def _metadata_inputs(layout: dict) -> dict[Path, bytes | None]:
    paths = [layout["state"] / "manifest.json"]
    if layout.get("registry"):
        paths.append(layout["registry"])
    return {path: _read(path) for path in paths}


def _validate_preconditions(
    approved: dict[Path, bytes | None], inventories: dict[Path, dict[str, bytes]]
) -> dict | None:
    """Compare against ownership evidence, never adopt a later edit as a baseline."""
    for inputs, reader in ((approved, _read), (inventories, _files)):
        for path, expected in inputs.items():
            try:
                current = reader(path)
            except (OSError, ValueError) as exc:
                return {
                    "status": "CONFLICT",
                    "reason": "managed inputs changed during validation; preserved",
                    "path": str(path),
                    "error_type": type(exc).__name__,
                }
            if current != expected:
                return {
                    "status": "CONFLICT",
                    "reason": "managed inputs changed during validation; preserved",
                    "path": str(path),
                }
    return None


def _transaction(
    layout: dict,
    writes: dict[Path, bytes | None],
    approved: dict[Path, bytes | None],
    inventories: dict[Path, dict[str, bytes]],
) -> dict | None:
    """Journal private before/after bytes, then activate each file atomically."""
    state = layout["state"]
    journal = state / "journal.json"
    changes = []
    for path, after in writes.items():
        before = approved[path]
        if before == after:
            continue
        changes.append({"path": str(path), "before": _encode(before), "after": _encode(after)})
    conflict = _validate_preconditions(approved, inventories)
    if conflict:
        return conflict
    record = {
        "phase": "plan",
        "root": str(layout["root"]),
        "config": str(layout["config"]),
        "changes": changes,
    }
    atomic_write(journal, json.dumps(record))
    try:
        for phase in ("stage", "validate", "activate"):
            record["phase"] = phase
            atomic_write(journal, json.dumps(record))
        for change in changes:
            path = Path(change["path"])
            if _read(path) != _decode(change["before"]):
                raise ValueError(f"target changed during activation: {path}")
            _write_bytes(path, _decode(change["after"]))
        record["phase"] = "verify"
        atomic_write(journal, json.dumps(record))
        for change in changes:
            if _read(Path(change["path"])) != _decode(change["after"]):
                raise ValueError("activated file failed verification")
        record["phase"] = "finalize"
        atomic_write(journal, json.dumps(record))
        journal.unlink()
    except BaseException:
        # The journal survives a failed rollback and can be recovered on the next invocation.
        _recover(layout)
        raise


def _encode(data: bytes | None) -> str | None:
    return base64.b64encode(data).decode("ascii") if data is not None else None


def _decode(data: str | None) -> bytes | None:
    return base64.b64decode(data, validate=True) if data is not None else None


def _write_bytes(path: Path, data: bytes | None) -> None:
    _safe(path)
    if data is None:
        path.unlink(missing_ok=True)
    else:
        # Deployed guides/configs are UTF-8; newline bytes are preserved.
        atomic_write(path, data.decode("utf-8"))


def _recover(layout: dict) -> None:
    journal = layout["state"] / "journal.json"
    raw = _read(journal)
    if raw is None:
        return
    record = json.loads(raw)
    if record.get("root") != str(layout["root"]) or record.get("config") != str(layout["config"]):
        raise ValueError("journal targets differ from selected integration")
    allowed = {layout["config"], layout["state"] / "manifest.json"}
    if layout.get("registry"):
        allowed.add(layout["registry"])
    changes = record.get("changes", [])
    for change in changes:
        path = Path(change["path"])
        _safe(path)
        if path not in allowed:
            relative = path.relative_to(layout["root"])
            if relative.parts[0] not in SKILLS.values() or ".." in relative.parts:
                raise ValueError("journal path outside managed targets")
        if _read(path) not in (_decode(change["before"]), _decode(change["after"])):
            raise ValueError(f"recovery conflict; later user edits preserved: {path}")
    if record.get("phase") != "finalize":
        for change in reversed(changes):
            _write_bytes(Path(change["path"]), _decode(change["before"]))
    journal.unlink()


def integrate(
    harness: str,
    scope: str = "user",
    skills: list[str] | None = None,
    dry_run: bool = False,
    command: str | None = None,
    project: Path | str | None = None,
    *,
    replace_managed_command: bool = False,
) -> dict:
    if harness == "all":
        results = [
            integrate(
                name,
                scope,
                skills,
                dry_run,
                command,
                project,
                replace_managed_command=replace_managed_command,
            )
            for name in HARNESSES
        ]
        successful = {"PREVIEW", "INSTALLED", "UNCHANGED"}
        return {
            "status": "PREVIEW"
            if dry_run and all(r["status"] in successful for r in results)
            else "COMPLETE"
            if all(r["status"] in successful for r in results)
            else "PARTIAL",
            "integrations": results,
        }
    layout = _layout(harness, scope, project)
    if "status" in layout:
        return layout
    if dry_run:
        return _integrate(layout, skills, True, command, replace_managed_command)
    with _locked(layout):
        _recover(layout)
        return _integrate(layout, skills, False, command, replace_managed_command)


def _integrate(
    layout: dict,
    selections: list[str] | None,
    dry_run: bool,
    command: str | None,
    replace_managed_command: bool = False,
) -> dict:
    from .capabilities import digest, guide_manifest, skill_root, tool_schemas

    approved = _metadata_inputs(layout)
    try:
        manifest = _load_manifest(layout)
        registry = _registry(layout)
    except (OSError, ValueError):
        conflict = _validate_preconditions(approved, {})
        if conflict:
            return conflict
        raise
    conflict = _validate_preconditions(approved, {})
    if conflict:
        return conflict
    inventories = {}
    selections = (
        selections
        if selections is not None
        else (manifest.get("selection") if manifest else ["core", "diagnostics"])
    )
    unknown = set(selections) - SKILLS.keys()
    if unknown:
        raise ValueError(f"unknown skill selections: {sorted(unknown)}")
    names = sorted({SKILLS[name] for name in selections})
    config_raw = _read(layout["config"])
    approved[layout["config"]] = config_raw
    original = (config_raw or b"").decode("utf-8")
    disabled = _disabled(layout, original, names)
    if disabled:
        return {"status": "DISABLED", "harness": layout["harness"], "skills": disabled}
    shadows = _shadowed(layout, names, original)
    if shadows:
        return {
            "status": "CONFLICT",
            "reason": "configured skill source may shadow or duplicate this target; preserved",
            "shadowed": shadows,
        }
    previous = server_entry(layout["harness"], original)
    if manifest and previous != manifest.get("mcp_entry"):
        return {"status": "CONFLICT", "reason": "managed MCP entry was modified; preserved"}
    # Retain an approved public launcher alias on repeat enrollment. The installer
    # may register its stable wrapper while this process runs under its venv Python.
    selected_command = command or (manifest.get("mcp_entry") or {}).get("command")
    preview = install_mcp(
        layout["harness"],
        layout["config"],
        selected_command,
        dry_run=True,
        managed_entry=manifest.get("mcp_entry") if replace_managed_command else None,
    )
    if preview["status"] in ("CONFLICT", "DISABLED"):
        return preview
    bundle = guide_manifest()
    sources = {}
    conflicts = []
    for name in names:
        source = _files(skill_root() / name)
        if "SKILL.md" not in source:
            raise ValueError(f"bundle lacks {name}/SKILL.md")
        hashes = _digests(source)
        expected = bundle["skills"][name]["sha256"]
        if hashes != expected:
            raise ValueError(f"bundle checksum mismatch: {name}")
        existing = _files(layout["root"] / name)
        inventories[layout["root"] / name] = existing
        managed = _managed_hashes(layout, manifest, name, registry)
        if not managed and layout.get("registry"):
            managed = registry["skills"].get(name, {}).get("files")
        if existing and (not managed or _digests(existing) != managed):
            conflicts.append({"name": name, "status": "MODIFIED" if managed else "CONFLICT"})
        sources[name] = source
    removed = set(manifest.get("skills", {})) - set(names)
    for name in sorted(removed):
        existing = _files(layout["root"] / name)
        inventories[layout["root"] / name] = existing
        if _digests(existing) != _managed_hashes(layout, manifest, name, registry):
            conflicts.append({"name": name, "status": "MODIFIED"})
    conflict = _validate_preconditions(approved, inventories)
    if conflict:
        return conflict
    if conflicts:
        # Leave a private comparison copy; never shadow it in a discoverable skill directory.
        if not dry_run:
            for conflict in conflicts:
                for relative, data in sources.get(conflict["name"], {}).items():
                    _write_bytes(layout["state"] / "proposed" / conflict["name"] / relative, data)
        return {
            "status": "CONFLICT",
            "skills": conflicts,
            "comparison": str(layout["state"] / "proposed"),
        }
    # Probe the selected installed launcher, not the Python module doing this deployment.
    # No model, capture, or GUI input is involved in the advertised discovery command.
    try:
        probe = subprocess.run(
            [preview["entry"]["command"], "capabilities", "--json"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        if probe.returncode:
            return {
                "status": "INCOMPATIBLE",
                "reason": "selected runtime capability probe failed",
                "exit_code": probe.returncode,
            }
        advertised = json.loads(probe.stdout)
        compatible = (
            advertised.get("runtime_version") == bundle["runtime_version"]
            and advertised.get("runtime_version", "0") in SpecifierSet(bundle["api_range"])
            and advertised.get("api_schema_version") == bundle["api_schema_version"]
            and advertised.get("guide_contract_version") == bundle["guide_contract_version"]
            and advertised.get("schema_sha256") == digest(tool_schemas())
            and set(bundle["required_tools"]) <= set(advertised.get("tools", []))
            and advertised.get("guides", {}).get("skills") == bundle["skills"]
        )
        if not compatible:
            return {
                "status": "INCOMPATIBLE",
                "reason": (
                    "runtime and guide release/schema/features differ; "
                    "select this release's executable"
                ),
            }
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {
            "status": "INCOMPATIBLE",
            "reason": f"runtime discovery unavailable: {type(exc).__name__}",
        }
    writes = {}
    installed = dict(manifest.get("skills", {}))
    for name in removed:
        managed = _managed_hashes(layout, manifest, name, registry)
        if _release_guide(layout, registry, name):
            for relative in managed:
                writes[layout["root"] / name / relative] = None
        del installed[name]
    for name, files in sources.items():
        target = layout["root"] / name
        for relative in _managed_hashes(layout, manifest, name, registry) or {}:
            if relative not in files:
                writes[target / relative] = None
        for relative, data in files.items():
            writes[target / relative] = data
        installed[name] = {
            "path": str(target),
            "realpath": str(target.resolve()),
            "files": _digests(files),
        }
        if layout.get("registry"):
            owners = registry["skills"].get(name, {}).get("owners", [])
            registry["skills"][name] = {
                "files": _digests(files),
                "owners": sorted(set([*owners, _owner(layout)])),
            }
    entry = {**dict(previous or {}), **preview["entry"]}
    updated = {
        "format": 1,
        "harness": layout["harness"],
        "profile": layout["profile"],
        "scope": layout["scope"],
        "root": str(layout["root"]),
        "config": str(layout["config"]),
        "project": layout["project"],
        "selection": sorted(set(selections)),
        "release": bundle["runtime_version"],
        "guide_contract_version": bundle["guide_contract_version"],
        "api_schema_version": bundle["api_schema_version"],
        "api_range": bundle["api_range"],
        "schema_sha256": advertised["schema_sha256"],
        "skills": installed,
        "mcp_entry": entry,
        "previous_mcp_entry": manifest.get(
            "previous_mcp_entry", dict(previous) if previous else None
        ),
        "owns_mcp": manifest.get("owns_mcp", False) or previous is None,
    }
    writes[layout["config"]] = render_entry(layout["harness"], original, entry).encode("utf-8")
    writes[layout["state"] / "manifest.json"] = (json.dumps(updated, indent=2) + "\n").encode()
    if layout.get("registry"):
        writes[layout["registry"]] = (json.dumps(registry, indent=2) + "\n").encode()
    for directory, files in inventories.items():
        for path in writes:
            if path.is_relative_to(directory):
                approved[path] = files.get(path.relative_to(directory).as_posix())
    conflict = _validate_preconditions(approved, inventories)
    if conflict:
        return conflict
    changed = [str(path) for path, data in writes.items() if _read(path) != data]
    if not dry_run and changed:
        conflict = _transaction(layout, writes, approved, inventories)
        if conflict:
            return conflict
    return {
        "status": "PREVIEW" if dry_run else "INSTALLED" if changed else "UNCHANGED",
        "harness": layout["harness"],
        "profile": layout["profile"],
        "scope": layout["scope"],
        "changed": changed,
        "skills": names,
        "manifest": str(layout["state"] / "manifest.json"),
        "stages": _stages("PASS" if not dry_run else "NOT_RUN"),
    }


def _stages(installed: str = "NOT_RUN") -> dict:
    return {
        name: {"status": installed if name == "INSTALLED" else "NOT_RUN"}
        for name in ("INSTALLED", "DISCOVERED", "LOADED", "INVOKED", "TASK_VERIFIED")
    }


def _jsonlines(output: str) -> list[dict]:
    events = []
    for line in output.splitlines():
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                events.append(value)
        except json.JSONDecodeError:
            continue
    return events


def _tool_result_failed(payload) -> bool:
    if not isinstance(payload, dict):
        return False
    details = payload.get("details")
    return bool(
        payload.get("isError")
        or payload.get("error")
        or isinstance(details, dict)
        and (details.get("isError") or details.get("error"))
    )


def _tool_result_succeeded(payload) -> bool:
    """A completed call is only invocation evidence when its result succeeded."""
    return isinstance(payload, dict) and bool(payload) and not _tool_result_failed(payload)


def _compatibility(manifest: dict) -> dict:
    from .capabilities import digest, guide_manifest, tool_schemas

    current = guide_manifest()
    agrees = (
        manifest.get("release") == current["runtime_version"]
        and manifest.get("guide_contract_version") == current["guide_contract_version"]
        and manifest.get("api_schema_version") == current["api_schema_version"]
        and manifest.get("schema_sha256") == digest(tool_schemas())
        and all(
            item["files"] == current["skills"][name]["sha256"]
            for name, item in manifest["skills"].items()
        )
    )
    return {
        "status": "MATCH" if agrees else "MISMATCH",
        "reload_required": not agrees,
        "installed_release": manifest.get("release"),
        "runtime_release": current["runtime_version"],
        "action": None
        if agrees
        else "refresh this managed integration and start a fresh harness session",
    }


def _probe_reason(output: str, code: int) -> str:
    # Do not return raw provider errors: they can include API keys or private endpoints.
    # Tool outputs include guide bodies and schemas, so their words are never
    # evidence of provider failure. Inspect transport/model error fields instead.
    diagnostics = []
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            if not line.startswith("CLEF_"):
                diagnostics.append(line)
            continue
        if not isinstance(event, dict):
            continue
        message = event.get("message")
        if isinstance(message, dict) and message.get("errorMessage"):
            diagnostics.append(str(message["errorMessage"]))
        if event.get("type") in ("error", "turn.failed") or (
            "type" not in event and "error" in event
        ):
            error = event.get("error", message)
            if isinstance(error, dict):
                error = error.get("message", error.get("errorMessage"))
            if error:
                diagnostics.append(str(error))
    lower = "\n".join(diagnostics).lower()
    if "401" in lower or "invalid_api_key" in lower:
        return (
            "provider rejected existing credentials (401/invalid_api_key); "
            "no guide/model invocation proved"
        )
    if "api key" in lower or "credential" in lower or "no model" in lower:
        return "provider authentication/model is unavailable; inspect private trace"
    if "deadline exceeded" in lower or "timed out" in lower:
        return "actual harness model/session deadline exceeded; inspect private trace"
    if "unable to connect" in lower or "connection refused" in lower:
        return "actual harness provider connection failed; inspect private trace"
    return f"actual harness exited {code}; inspect private trace"


def _verification_prompt(trigger: str) -> str:
    prompts = {
        "natural": (
            "Determine whether the installed local runtime can assess whether Blender's "
            "File menu is open without sending input; report its current supported "
            "runtime capabilities. Do not capture or change the desktop, or download anything."
        ),
        "explicit": (
            "Use the clef-use guide to inspect local capabilities without capturing "
            "the screen, changing focus, sending input, downloading, or modifying files."
        ),
        "negative": (
            "Explain how a Python list comprehension differs from a generator expression. "
            "Do not access the GUI, local files, or runtime tools."
        ),
    }
    if trigger not in prompts:
        raise ValueError("trigger must be natural, explicit, negative or native")
    return prompts[trigger]


def _hermes_command(
    executable: str,
    cwd: Path,
    path: Path | None,
    transcript: bool = False,
    read_only_entry: dict | None = None,
) -> list:
    launch = subprocess.run(
        [executable, "--print-runtime-command"],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if launch.returncode:
        raise ValueError("installed Hermes launcher cannot advertise its runtime command")
    command = json.loads(launch.stdout)
    if not isinstance(command, list) or len(command) != 4 or command[1:3] != ["-I", "-c"]:
        raise ValueError("unsupported Hermes runtime command; native adapter not executed")
    bootstrap = ast.parse(command[3])
    call = bootstrap.body[-1]
    if not (
        isinstance(call, ast.Expr)
        and isinstance(call.value, ast.Call)
        and isinstance(call.value.func, ast.Attribute)
        and call.value.func.attr == "run_module"
    ):
        raise ValueError("Hermes bootstrap entrypoint differs; native adapter not executed")
    if read_only_entry is not None:
        # Native Hermes filters parent environment variables before MCP spawn.
        # Set the selected server's permission in its in-memory native config;
        # retain the original CLI entrypoint, model, auth and generated prompt.
        hook = f"""
import functools as _clef_functools
import model_tools as _clef_model_tools
from tools.registry import registry as _clef_registry, tool_error as _clef_tool_error
from tools import mcp_tool_discovery as _clef_discovery
_clef_definitions = _clef_model_tools.get_tool_definitions
@_clef_functools.wraps(_clef_definitions)
def _clef_read_only_definitions(*args, **kwargs):
    # Native MCP refresh rebuilds schemas after the one-shot constructor prune.
    # Filtering the native factory also bounds deferred search/describe/call.
    return [tool for tool in _clef_definitions(*args, **kwargs)
            if tool.get('function', {{}}).get('name') != 'skill_manage']
_clef_model_tools.get_tool_definitions = _clef_read_only_definitions
_clef_dispatch = _clef_registry.dispatch
@_clef_functools.wraps(_clef_dispatch)
def _clef_read_only_dispatch(name, args, **kwargs):
    if name == 'skill_manage':
        return _clef_tool_error('Skill modifications are forbidden during read-only verification')
    return _clef_dispatch(name, args, **kwargs)
_clef_registry.dispatch = _clef_read_only_dispatch
_clef_register = _clef_discovery.register_mcp_servers
def _clef_read_only_register(servers):
    selected = {{}}
    if 'clef-use' in servers:
        config = dict(servers['clef-use'])
        if (config.get('command') != {read_only_entry["command"]!r}
                or config.get('args', []) != {read_only_entry.get("args", [])!r}):
            raise ValueError('selected native MCP entry changed before verification')
        config['env'] = {{**config.get('env', {{}}), 'CLEF_USE_MCP_READ_ONLY': '1'}}
        selected['clef-use'] = config
    return _clef_register(selected)
_clef_discovery.register_mcp_servers = _clef_read_only_register
"""
        bootstrap.body[-1:-1] = ast.parse(hook).body
        command[3] = ast.unparse(bootstrap)
    elif transcript:
        # The ordinary bootstrap may finish a dependency update. Transcript reads
        # use the same committed native environment without taking updater locks.
        sources = [
            node.args[1].value
            for node in ast.walk(bootstrap)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and ast.unparse(node.func) == "sys.path.insert"
            and len(node.args) == 2
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == 0
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
        ]
        if len(sources) != 1 or not Path(sources[0]).is_absolute():
            raise ValueError("Hermes launcher did not identify one native source root")
        command[3] = (
            "import sys,site,runpy;from pathlib import Path;"
            f"sys.path.insert(0,{sources[0]!r});"
            "from pm.environments import committed_venv,site_packages;"
            f"environment=committed_venv(Path({sources[0]!r}));"
            "assert environment is not None;site.addsitedir(str(site_packages(environment)));"
            f"runpy.run_path({str(path)!r},run_name='__main__')"
        )
    else:
        if path is None:
            raise ValueError("native Hermes probe path is required")
        bootstrap.body[-1] = ast.parse(f"runpy.run_path({str(path)!r}, run_name='__main__')").body[
            0
        ]
        command[3] = ast.unparse(bootstrap)
    return command


def _hermes_native(layout: dict, manifest: dict, executable: str, cwd: Path, result: dict) -> dict:
    script = r"""
import hashlib, json
from pathlib import Path
from tools.skills_tool import _skill_catalog, skill_view
from hermes_cli.config import load_config
from tools.mcp_tool_discovery import register_mcp_servers
from tools.mcp_tool_lifecycle import shutdown_mcp_servers
from tools.mcp_tool_schema import mcp_prefixed_tool_name
from tools.registry import registry
NAMES = __NAMES__
catalog = [s for s in _skill_catalog() if s['load_name'] in NAMES]
loaded = []
for skill in catalog:
    view = json.loads(skill_view(skill['load_name']))
    raw = Path(skill['path']).read_text()
    body = raw.split('---',2)[2].strip()
    loaded.append({'name':skill['load_name'], 'path':str(skill['path']),
       'sha256':hashlib.sha256(raw.encode()).hexdigest(),
       'contentLoaded':view.get('success') and body in view.get('content',''),
       'source':view.get('_source_path')})
print('CLEF_DISCOVERY:' + json.dumps({'loaded':loaded}), flush=True)
config = dict(load_config()['mcp_servers']['clef-use'])
config['env'] = {**config.get('env', {}), 'CLEF_USE_MCP_READ_ONLY':'1'}
try:
    names = register_mcp_servers({'clef-use':config})
    name = mcp_prefixed_tool_name('clef-use','computer_capabilities')
    if name not in names: raise RuntimeError('native registry did not discover capability tool')
    tool = registry.get_entry(name)
    payload = tool.handler({'detail':True})
    if isinstance(payload,str): payload = json.loads(payload)
    print('CLEF_INVOKED:' + json.dumps({'tool':name,'result':payload}))
finally:
    shutdown_mcp_servers()
""".replace("__NAMES__", repr(list(manifest["skills"])))
    path = layout["state"] / "verification-hermes-native.py"
    atomic_write(path, script)
    try:
        command = _hermes_command(executable, cwd, path)
        run = subprocess.run(
            command,
            cwd=cwd,
            env={**os.environ, "CLEF_USE_MCP_READ_ONLY": "1"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
        )
    finally:
        path.unlink(missing_ok=True)
    trace = layout["state"] / "verification-native-trace.txt"
    atomic_write(trace, run.stdout + run.stderr)
    discovery = next(
        (
            json.loads(line.removeprefix("CLEF_DISCOVERY:"))
            for line in run.stdout.splitlines()
            if line.startswith("CLEF_DISCOVERY:")
        ),
        {},
    )
    loaded = [
        item["name"]
        for item in discovery.get("loaded", [])
        if item.get("contentLoaded")
        and item.get("path") == item.get("source")
        and item["name"] in manifest["skills"]
        and str(Path(item["path"]).resolve())
        == str((layout["root"] / item["name"] / "SKILL.md").resolve())
        and item["sha256"] == manifest["skills"][item["name"]]["files"]["SKILL.md"]
    ]
    invoked = next(
        (
            json.loads(line.removeprefix("CLEF_INVOKED:"))
            for line in run.stdout.splitlines()
            if line.startswith("CLEF_INVOKED:")
        ),
        {},
    )
    succeeded = _tool_result_succeeded(invoked.get("result"))
    payload = _native_payload(json.dumps(invoked.get("result")), invoked.get("tool", ""))
    read_only_scope = (
        isinstance(payload, dict)
        and payload.get("read_only_facade") is True
        and _capability_agrees(payload, manifest, detail=True)
    )
    stages = result["stages"]
    stages["DISCOVERED"] = {
        "status": "PASS" if set(loaded) == set(manifest["skills"]) else "NOT_RUN",
        "skills": loaded,
    }
    stages["LOADED"] = {
        "status": "PASS" if set(loaded) == set(manifest["skills"]) else "NOT_RUN",
        "skills": loaded,
    }
    stages["INVOKED"] = {
        "status": "PASS"
        if succeeded
        else "FAIL"
        if _tool_result_failed(invoked.get("result"))
        else "NOT_RUN",
        "tools": [invoked["tool"]] if succeeded else [],
    }
    result.update(
        native_trace=str(trace),
        native_exit_code=run.returncode,
        model_driven=False,
        method="installed Hermes native catalog/skill_view/MCP registry; no model task",
        native_read_only_scope={
            "status": "PASS" if read_only_scope else "FAIL",
            "method": "native MCP server environment and live two-tool schema",
        },
    )
    result["status"] = (
        "PASS"
        if set(loaded) == set(manifest["skills"]) and succeeded and read_only_scope
        else "FAIL"
        if _tool_result_failed(invoked.get("result"))
        else "NOT_RUN"
    )
    if run.returncode:
        result["status"] = "FAIL"
        result["native_reason"] = _probe_reason(run.stdout + run.stderr, run.returncode)
    return result


def _capability_agrees(payload: dict, manifest: dict, *, detail: bool) -> bool:
    from .capabilities import digest, tool_schemas

    guides = payload.get("guides")
    if not isinstance(guides, dict) or not isinstance(guides.get("skills"), dict):
        return False
    for skill, item in manifest["skills"].items():
        advertised = guides["skills"].get(skill)
        if (
            not isinstance(advertised, dict)
            or not isinstance(advertised.get("sha256"), dict)
            or advertised["sha256"].get("SKILL.md") != item["files"]["SKILL.md"]
        ):
            return False
    expected = manifest["schema_sha256"]
    if payload.get("read_only_facade") is True:
        schemas = tool_schemas()
        names = ("computer_capabilities", "computer_status")
        expected = digest({name: schemas[name] for name in names})
        tools = payload.get("tools")
        if not isinstance(tools, list) or not all(isinstance(name, str) for name in tools):
            return False
        if set(tools) != set(names):
            return False
    return (
        payload.get("runtime_version") == manifest["release"]
        and payload.get("schema_sha256") == expected
        and (
            not detail
            or isinstance(payload.get("schemas"), dict)
            and digest(payload["schemas"]) == expected
        )
    )


_HERMES_TRANSCRIPT_LIMIT = 10 * 1024 * 1024
_HERMES_MODEL_TOOLS = (
    "skill_view",
    "mcp__clef_use__computer_capabilities",
    "mcp__clef_use__computer_status",
    # Native Hermes adds these read-only MCP protocol adapters to the catalog.
    # They remain attempts/errors, but cannot prove product-tool invocation.
    "mcp__clef_use__list_resources",
    "mcp__clef_use__read_resource",
    "mcp__clef_use__list_prompts",
    "mcp__clef_use__get_prompt",
)


def _hermes_session_id(events: list[dict]) -> str:
    initial = [e for e in events if e.get("type") == "system" and e.get("subtype") == "init"]
    terminal = [e for e in events if e.get("type") == "result"]
    if len(initial) != 1 or len(terminal) != 1:
        raise ValueError("Hermes stream must identify one initial and terminal session")
    session = initial[0].get("session_id")
    if (
        not isinstance(session, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", session)
        or terminal[0].get("session_id") != session
    ):
        raise ValueError("Hermes stream session identities disagree")
    return session


def _hermes_transcript(
    layout: dict, executable: str, cwd: Path, events: list[dict], trigger: str
) -> dict:
    session = _hermes_session_id(events)
    _safe(layout["config"].parent / "state.db")
    path = layout["state"] / f"verification-{trigger}-transcript-reader.py"
    script = f"""
import inspect,json
from pathlib import Path
from hermes_state import SessionDB
from hermes_state_portability import SessionPortabilityMixin
db=SessionDB(db_path=Path({str(layout["config"].parent / "state.db")!r}),read_only=True)
try:
    db.assert_export_safe({session!r},max_messages=1000)
    exported=db.export_session({session!r},include_inactive=True)
    if not exported or exported['id']!={session!r}:
        raise ValueError('selected native session absent')
    data={{'id':exported['id'],'model':exported.get('model'),'messages':exported['messages'],
          'provenance':{{'sessiondb_module':inspect.getfile(SessionDB),
          'export_module':inspect.getfile(SessionPortabilityMixin),'read_only':True}}}}
    encoded=json.dumps(data,ensure_ascii=True)
    if len(encoded.encode())>{_HERMES_TRANSCRIPT_LIMIT}:
        raise ValueError('native transcript exceeds bound')
    print(encoded)
finally:
    db.close()
"""
    atomic_write(path, script)
    try:
        command = _hermes_command(executable, cwd, path, transcript=True)
        run = subprocess.run(
            command,
            cwd=cwd,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    finally:
        path.unlink(missing_ok=True)
    atomic_write(layout["state"] / f"verification-{trigger}-transcript.stderr", run.stderr)
    if run.returncode or len(run.stdout.encode()) > _HERMES_TRANSCRIPT_LIMIT:
        raise ValueError("installed Hermes read-only session export unavailable or exceeds bound")
    transcript = json.loads(run.stdout)
    archive = layout["state"] / f"verification-{trigger}-transcript.json"
    atomic_write(archive, run.stdout)
    return transcript


def _native_payload(content: str, name: str, depth: int = 0):
    """Decode complete native output, retaining errors at every envelope level."""
    if depth >= 6:
        return None
    if not isinstance(content, str) or len(content.encode()) > _HERMES_TRANSCRIPT_LIMIT:
        raise ValueError("Hermes response exceeds bound")
    value = content
    for _ in range(6):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                return None
        elif isinstance(value, dict):
            if _tool_result_failed(value):
                return value
            if "result" in value and set(value) <= {"result", "structuredContent", "_meta"}:
                if "structuredContent" in value:
                    structured = _native_payload(
                        json.dumps(value["structuredContent"]), name, depth + 1
                    )
                    if structured is None or _tool_result_failed(structured):
                        return structured
                value = value["result"]
            else:
                return value or None
        else:
            return None
    return None


def _hermes_output_candidates(layout: dict, call: dict, message: dict) -> list[str]:
    raw, name, identity = message.get("content"), call["name"], call["tool_call_id"]
    if not isinstance(raw, str):
        raise ValueError("Hermes canonical result content is invalid")
    if raw.startswith("<untrusted_tool_result"):
        if (
            not raw.startswith(f'<untrusted_tool_result source="{name}">\n')
            or not raw.endswith("\n</untrusted_tool_result>")
            or "\n\n" not in raw
        ):
            raise ValueError("Hermes canonical result wrapper disagrees with tool")
        raw = raw.split("\n\n", 1)[1].removesuffix("\n</untrusted_tool_result>")
    spill = re.search(r"^Full output saved to: (.+)$", raw, re.M)
    if spill:
        expected = layout["config"].parent / "cache/spillover" / f"{identity}.txt"
        path = Path(spill[1].strip())
        if "<persisted-output>" not in raw or path != expected:
            raise ValueError("Hermes spillover is outside the selected profile and call")
        _safe(path)
        if not path.is_file() or path.stat().st_size > _HERMES_TRANSCRIPT_LIMIT:
            raise ValueError("Hermes spillover is absent or exceeds bound")
        with path.open("rb") as stream:
            value = stream.read(_HERMES_TRANSCRIPT_LIMIT + 1)
        if len(value) > _HERMES_TRANSCRIPT_LIMIT:
            raise ValueError("Hermes spillover exceeds bound")
        raw = value.decode("utf-8")
        if name.startswith("mcp__"):
            # The native MCP handler envelopes losslessly persisted text.
            return [raw, json.dumps({"result": raw}, ensure_ascii=False)]
    return [raw]


def _hermes_matching_outputs(output, candidates: list[str]) -> list[str]:
    if not isinstance(output, str) or not output:
        return []
    return [
        candidate
        for candidate in candidates
        if candidate == output
        or len(output) == 5003
        and output.endswith("...")
        and len(candidate) > 5000
        and candidate[:5000] == output[:5000]
    ]


def _hermes_model_evidence(
    layout: dict, manifest: dict, events: list[dict], transcript: dict, trigger: str
) -> dict:
    session = _hermes_session_id(events)
    if not isinstance(transcript, dict) or transcript.get("id") != session:
        raise ValueError("Hermes exported session disagrees with native stream")
    messages = transcript.get("messages")
    if (
        not isinstance(messages, list)
        or len(messages) > 1000
        or len(json.dumps(transcript).encode()) > _HERMES_TRANSCRIPT_LIMIT
    ):
        raise ValueError("Hermes canonical transcript exceeds bound")
    calls, results, ordered, message_ids = {}, {}, [], set()
    for message in messages:
        if (
            not isinstance(message, dict)
            or type(message.get("id")) not in (str, int)
            or message.get("id") == ""
        ):
            raise ValueError("Hermes canonical message identity is invalid")
        if message["id"] in message_ids:
            raise ValueError("Hermes canonical message identities are ambiguous")
        message_ids.add(message.get("id"))
        native_calls = message.get("tool_calls")
        if native_calls is None:
            native_calls = []
        if isinstance(native_calls, str):
            native_calls = json.loads(native_calls)
        if not isinstance(native_calls, list) or (
            native_calls and message.get("role") != "assistant"
        ):
            raise ValueError("Hermes calls must belong to an assistant message")
        for call in native_calls:
            if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
                raise ValueError("Hermes canonical call shape is invalid")
            identity = call.get("id")
            if (
                not isinstance(identity, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", identity)
                or identity in calls
                or call.get("call_id", identity) != identity
            ):
                raise ValueError("Hermes canonical call identities are ambiguous")
            function = call.get("function", {})
            name, arguments = function.get("name"), function.get("arguments", {})
            if not isinstance(name, str):
                raise ValueError("Hermes canonical tool name is invalid")
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            if name == "tool_call":
                inner = arguments.get("calls") if isinstance(arguments, dict) else None
                if not isinstance(inner, list) or len(inner) != 1 or not isinstance(inner[0], dict):
                    raise ValueError("Hermes aggregate tool call cannot be linked unambiguously")
                name, arguments = inner[0].get("name"), inner[0].get("arguments")
            if not isinstance(name, str) or not isinstance(arguments, dict):
                raise ValueError("Hermes canonical tool arguments are invalid")
            calls[identity] = {"tool_call_id": identity, "name": name, "arguments": arguments}
            if name in _HERMES_MODEL_TOOLS:
                ordered.append(calls[identity])
        if message.get("role") == "tool":
            identity = message.get("tool_call_id")
            if (
                identity not in calls
                or identity in results
                or message.get("tool_name") != calls[identity]["name"]
            ):
                raise ValueError("Hermes canonical result has no unique matching native call")
            results[identity] = message
    loaded, invoked, attempted, failed_calls, responses = [], [], [], [], []
    response_bytes = cached_bytes = 0
    output_cache = {}

    def outputs(call):
        nonlocal cached_bytes
        identity = call["tool_call_id"]
        if identity not in output_cache:
            if identity not in results:
                raise ValueError("Hermes canonical response is absent")
            values = _hermes_output_candidates(layout, call, results[identity])
            cached_bytes += sum(len(value.encode()) for value in values)
            if cached_bytes > _HERMES_TRANSCRIPT_LIMIT:
                raise ValueError("Hermes recovered response candidates exceed bound")
            output_cache[identity] = values
        return output_cache[identity]

    expected = (
        "clef-use-blender"
        if trigger == "natural" and "clef-use-blender" in manifest["skills"]
        else "clef-use"
    )
    runtime_before_guide = False
    pending, position, completed, any_gui_guide = {}, 0, set(), False
    for event in events:
        name, kind = event.get("name"), event.get("type")
        if name not in _HERMES_MODEL_TOOLS or kind not in ("tool_use", "tool_result"):
            continue
        if kind == "tool_use":
            if position >= len(ordered):
                raise ValueError("Hermes stream call is absent from selected native session")
            call = ordered[position]
            position += 1
            if (
                name != call["name"]
                or event.get("input") != call["arguments"]
                or event.get("tool_call_id", call["tool_call_id"]) != call["tool_call_id"]
            ):
                raise ValueError("Hermes stream call identity or arguments disagree")
            pending.setdefault(name, []).append(call)
            if (
                name
                in (
                    "mcp__clef_use__computer_capabilities",
                    "mcp__clef_use__computer_status",
                )
                and expected not in loaded
            ):
                runtime_before_guide = True
            if name.startswith("mcp__") and name not in attempted:
                attempted.append(name)
            if name == "skill_view" and event["input"].get("name") in (
                "computer-use",
                *SKILLS.values(),
            ):
                any_gui_guide = True
            continue
        waiting = pending.get(name, [])
        if not waiting:
            raise ValueError("Hermes stream result has no matching call")
        if event.get("tool_call_id"):
            candidates = [c for c in waiting if c["tool_call_id"] == event["tool_call_id"]]
        elif len(waiting) == 1:
            candidates = waiting
        else:
            # Match bytes against every complete, identity-bound native result.
            # Shared prefixes remain ambiguous; never guess FIFO completion.
            candidates = [
                c for c in waiting if _hermes_matching_outputs(event.get("output"), outputs(c))
            ]
        if len(candidates) != 1:
            raise ValueError("Hermes concurrent stream result identities are ambiguous")
        call = candidates[0]
        waiting.remove(call)
        identity = call["tool_call_id"]
        if (
            event.get("tool_call_id", identity) != identity
            or identity in completed
            or identity not in results
        ):
            raise ValueError("Hermes stream result identities disagree")
        completed.add(identity)
        matched = _hermes_matching_outputs(event.get("output"), outputs(call))
        if len(matched) != 1:
            raise ValueError("Hermes canonical response disagrees with native stream bytes")
        raw = matched[0]
        response_bytes += len(raw.encode())
        if response_bytes > _HERMES_TRANSCRIPT_LIMIT:
            raise ValueError("Hermes recovered responses exceed total bound")
        payload = _native_payload(raw, name)
        responses.append({"tool_call_id": identity, "tool": name, "content": raw})
        if event.get("is_error") or _tool_result_failed(payload):
            failed_calls.append(
                {"tool_call_id": identity, "tool": name, "response_sha256": _hash(raw.encode())}
            )
            continue
        if name == "skill_view":
            skill = call["arguments"].get("name")
            if (
                skill in manifest["skills"]
                and not call["arguments"].get("file_path")
                and isinstance(payload, dict)
            ):
                path = layout["root"] / skill / "SKILL.md"
                body = path.read_text().split("---", 2)[-1].strip()
                if (
                    payload.get("success") is True
                    and payload.get("_source_path") == str(path.resolve())
                    and _hash(path.read_bytes()) == manifest["skills"][skill]["files"]["SKILL.md"]
                    and body in payload.get("content", "")
                ):
                    loaded.append(skill)
        elif name.endswith("computer_capabilities") and isinstance(payload, dict):
            if _capability_agrees(payload, manifest, detail=bool(call["arguments"].get("detail"))):
                invoked.append(name)
        elif name.endswith("computer_status") and _tool_result_succeeded(payload):
            invoked.append(name)
    if position != len(ordered) or any(call["tool_call_id"] not in completed for call in ordered):
        raise ValueError("Hermes canonical and stream call inventories disagree")
    violations = list(
        dict.fromkeys(
            name
            for name in [
                *(
                    event.get("name")
                    for event in events
                    if event.get("type") in {"tool_use", "tool_result"}
                ),
                *(call["name"] for call in calls.values()),
            ]
            if isinstance(name, str)
            and (
                name == "skill_manage"
                or name.startswith("mcp__clef_use__")
                and name not in _HERMES_MODEL_TOOLS
            )
        )
    )
    passed = not violations and (
        not any_gui_guide and not attempted
        if trigger == "negative"
        else expected in loaded and bool(invoked) and not failed_calls and not runtime_before_guide
    )
    observed_violation = bool(
        violations
        or failed_calls
        or runtime_before_guide
        or trigger == "negative"
        and (any_gui_guide or attempted)
    )
    return {
        "case": trigger,
        "session_id": session,
        "status": "PASS" if passed else "FAIL",
        "loaded": loaded,
        "invoked": invoked,
        "attempted": attempted,
        "failed_calls": failed_calls,
        "read_only_violations": violations,
        "observed_violation": observed_violation,
        "runtime_before_guide": runtime_before_guide,
        "load_before_invoke": bool(invoked) and not runtime_before_guide,
        "stages": _model_stages(loaded, invoked, bool(failed_calls)),
        "_responses": responses,
    }


def _verify_hermes(
    layout: dict, manifest: dict, executable: str, cwd: Path, result: dict, trigger: str
) -> dict:
    result = _hermes_native(layout, manifest, executable, cwd, result)
    if trigger == "native":
        return result
    if result["native_exit_code"]:
        result["reason"] = "native Hermes preflight failed; model not started"
        return result
    if result["native_read_only_scope"]["status"] != "PASS":
        result["status"] = "FAIL"
        result["reason"] = "native Hermes read-only MCP scope was not proven; model not started"
        return result
    environment = {**os.environ, "CLEF_USE_MCP_READ_ONLY": "1", "NO_COLOR": "1", "COLUMNS": "200"}
    listed = subprocess.run(
        [executable, "skills", "list", "--enabled-only", "--source", "local"],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    trace = layout["state"] / "verification-discovery.txt"
    atomic_write(trace, listed.stdout)
    matches = [
        name
        for name in manifest["skills"]
        if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", listed.stdout)
    ]
    result["cli_discovery"] = {
        "status": "PASS"
        if listed.returncode == 0 and set(matches) == set(manifest["skills"])
        else "FAIL",
        "skills": matches,
        "trace": str(trace),
        "method": "native CLI enabled skill catalog",
    }
    if result["cli_discovery"]["status"] != "PASS":
        result["status"] = "FAIL"
        result["reason"] = _probe_reason(listed.stderr, listed.returncode)
        return result
    prompt = _verification_prompt(trigger)
    run = subprocess.run(
        _hermes_command(executable, cwd, None, read_only_entry=manifest["mcp_entry"])
        + [
            "chat",
            "--oneshot",
            "--format",
            "stream-json",
            "--max-turns",
            "8",
            "--run-budget",
            "90",
            "--toolsets",
            # Hermes' spawn filter expects the raw configured server key.
            "skills,clef-use",
            "--in",
            str(cwd),
            "-q",
            prompt,
        ],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    events = _jsonlines(run.stdout)
    trace = layout["state"] / f"verification-{trigger}-trace.jsonl"
    atomic_write(trace, run.stdout)
    atomic_write(trace.with_suffix(".stderr"), run.stderr)
    result.update(
        trace=str(trace),
        exit_code=run.returncode,
        model_driven=True,
        native_method=result.get("method"),
        method=(
            "installed Hermes native catalog/MCP registry + model CLI and canonical transcript; "
            "in-memory read-only MCP permission overlay"
        ),
    )
    try:
        transcript = _hermes_transcript(layout, executable, cwd, events, trigger)
        evidence = _hermes_model_evidence(layout, manifest, events, transcript, trigger)
        responses = evidence.pop("_responses")
        archive = layout["state"] / f"verification-{trigger}-canonical-results.json"
        atomic_write(archive, json.dumps(responses, ensure_ascii=True))
        evidence["canonical_transcript"] = {
            "method": "installed Hermes SessionDB(read_only=True).export_session",
            "transcript_sha256": _hash(json.dumps(transcript, sort_keys=True).encode()),
            "responses_sha256": _hash(archive.read_bytes()),
            "response_count": len(responses),
        }
        if run.returncode and not evidence["observed_violation"]:
            evidence["status"] = "NOT_RUN"
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired):
        negative_attempt = trigger == "negative" and any(
            event.get("type") == "tool_use"
            and (
                str(event.get("name", "")).startswith("mcp__clef_use__")
                or event.get("name") == "skill_manage"
                or event.get("name") == "skill_view"
                and isinstance(event.get("input"), dict)
                and event["input"].get("name") in ("computer-use", *SKILLS.values())
            )
            for event in events
        )
        evidence = {
            "case": trigger,
            # A forbidden attempt disproves a negative trigger even if its
            # result/export is incomplete; incompleteness cannot erase it.
            "status": "FAIL" if negative_attempt else "NOT_RUN",
            "loaded": [],
            "invoked": [],
            "attempted": list(
                dict.fromkeys(
                    e["name"]
                    for e in events
                    if e.get("type") == "tool_use" and e.get("name") in _HERMES_MODEL_TOOLS[1:]
                )
            ),
            "stages": _model_stages([], [], False),
            "reason": (
                "complete linked native Hermes transcript unavailable; inspect private evidence"
            ),
        }
    result["model_trigger_verification"] = evidence
    if result["model_trigger_verification"]["status"] == "FAIL":
        result["status"] = "FAIL"
    elif result["model_trigger_verification"]["status"] == "NOT_RUN":
        result["status"] = "NOT_RUN"
    if run.returncode:
        result["reason"] = _probe_reason(run.stdout + run.stderr, run.returncode)
    return result


def _model_stages(loaded: list[str], invoked: list[str], failed: bool) -> dict:
    return {
        "LOADED": {"status": "PASS" if loaded else "NOT_RUN", "skills": loaded},
        "INVOKED": {
            "status": "FAIL" if failed else "PASS" if invoked else "NOT_RUN",
            "tools": invoked,
        },
    }


def _omp_read_only_policy(policies: dict) -> dict:
    """Tighten native approval policies without changing persistent configuration."""
    if not isinstance(policies, dict) or not all(isinstance(key, str) for key in policies):
        raise ValueError("native OMP approval policies are unavailable")
    approval = dict.fromkeys(policies, "deny")
    for name in (
        "read",
        "mcp__clef_use_computer_capabilities",
        "mcp__clef_use_computer_status",
    ):
        previous = policies.get(name)
        previous = previous.strip().lower() if isinstance(previous, str) else None
        approval[name] = (
            previous if previous in ("deny", "prompt") else None if name == "read" else "allow"
        )
    approval["write"] = "deny"
    return {
        "tools": {"approvalMode": "always-ask", "approval": approval},
        # Native OMP force-adds learning writers even to an explicit --tools list.
        "autolearn": {"enabled": False},
        # Validate against live discovery, not startup-window cached schemas.
        "mcp": {"startupTimeoutMs": 0},
    }


def _verify_omp_model(
    layout: dict,
    manifest: dict,
    executable: str,
    cwd: Path,
    result: dict,
    trigger: str,
    approval_policies: dict,
) -> dict:
    policy = layout["state"] / "verification-omp-read-only.json"
    atomic_write(policy, json.dumps(_omp_read_only_policy(approval_policies)))
    try:
        run = subprocess.run(
            [
                executable,
                "--print",
                "--mode",
                "json",
                "--no-session",
                "--no-extensions",
                "--no-lsp",
                "--max-time",
                "90",
                "--config",
                str(policy),
                "--approval-mode",
                "always-ask",
                "--tools",
                "read,mcp__clef_use_computer_capabilities,mcp__clef_use_computer_status",
                "--cwd",
                str(cwd),
                _verification_prompt(trigger),
            ],
            cwd=cwd,
            env={**os.environ, "CLEF_USE_MCP_READ_ONLY": "1"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
    finally:
        policy.unlink(missing_ok=True)
    trace = layout["state"] / f"verification-{trigger}-trace.jsonl"
    atomic_write(trace, run.stdout + run.stderr)
    events = _jsonlines(run.stdout)
    evidence = _omp_model_evidence(layout, manifest, events, trigger, run.returncode, cwd)
    result.update(
        trace=str(trace),
        model_driven=True,
        exit_code=run.returncode,
        model_trigger_verification=evidence,
        status=evidence["status"],
        permission_method="native temporary approval overlay; no persistent configuration changes",
    )
    if run.returncode:
        result["reason"] = _probe_reason(run.stdout + run.stderr, run.returncode)
    return result


def _omp_model_evidence(
    layout: dict, manifest: dict, events: list[dict], trigger: str, exit_code: int, cwd: Path
) -> dict:
    readers = ("mcp__clef_use_computer_capabilities", "mcp__clef_use_computer_status")
    allowed = ("read", "tool_search", *readers)
    starts, completed = {}, set()
    loaded, invoked, attempted, failed_calls, violations = [], [], [], [], []
    invalid = False
    any_gui_guide = False
    expected = (
        "clef-use-blender"
        if trigger == "natural" and "clef-use-blender" in manifest["skills"]
        else "clef-use"
    )
    runtime_before_guide = False

    def device_call(event: dict) -> tuple[str, dict] | None:
        arguments = event.get("args")
        if event.get("toolName") != "write" or not isinstance(arguments, dict):
            return None
        target = next((name for name in readers if arguments.get("path") == f"xd://{name}"), None)
        if target is None or not isinstance(arguments.get("content"), str):
            return None
        try:
            supplied = json.loads(arguments["content"])
        except ValueError:
            return None
        if not isinstance(supplied, dict):
            return None
        # Native device dispatch removes its string intent annotation before
        # validating these MCP schemas, which do not declare an intent field.
        if isinstance(supplied.get("i"), str):
            supplied.pop("i")
        if target == readers[0]:
            valid = (
                not supplied.keys() - {"detail", "operation_id"}
                and isinstance(supplied.get("detail", False), bool)
                and (
                    supplied.get("operation_id") is None
                    or isinstance(supplied["operation_id"], str)
                )
            )
        else:
            valid = not supplied.keys() - {"session_id"} and (
                supplied.get("session_id") is None or isinstance(supplied["session_id"], str)
            )
        return (target, supplied) if valid else None

    def device_matches(payload: dict, name: str, arguments: dict) -> bool:
        details = payload.get("details")
        native = details.get("xdev") if isinstance(details, dict) else None
        if (
            not isinstance(native, dict)
            or native.get("tool") != name
            or native.get("mode") != "execute"
        ):
            return False
        validated = native.get("args")
        defaults = (
            {"detail": False, "operation_id": None} if name == readers[0] else {"session_id": None}
        )
        if not isinstance(validated, dict) or json.dumps(
            {**defaults, **validated}, sort_keys=True
        ) != json.dumps({**defaults, **arguments}, sort_keys=True):
            return False
        inner = native.get("inner")
        return (
            isinstance(inner, dict)
            and inner.get("serverName") == "clef-use"
            and inner.get("mcpToolName") == name.removeprefix("mcp__clef_use_")
            and inner.get("isError") is False
            and isinstance(inner.get("rawContent"), list)
            and payload.get("content") == inner["rawContent"]
        )

    def guide_matches(path: str, skill: str) -> bool:
        physical = Path(path)
        return (
            path == f"skill://{skill}"
            or (physical if physical.is_absolute() else cwd / physical).resolve()
            == (layout["root"] / skill / "SKILL.md").resolve()
        )

    for event in events:
        kind, name, identity = event.get("type"), event.get("toolName"), event.get("toolCallId")
        if kind not in ("tool_execution_start", "tool_execution_end"):
            continue
        if not isinstance(name, str) or not isinstance(identity, str) or not identity:
            invalid = True
            continue
        if kind == "tool_execution_start":
            device = device_call(event)
            if device is not None:
                name, arguments = device
            else:
                arguments = event.get("args")
            if name not in allowed and name not in violations:
                violations.append(name)
            if name in readers and name not in attempted:
                attempted.append(name)
            if name in readers and expected not in loaded:
                runtime_before_guide = True
            if identity in starts or not isinstance(event.get("args"), dict):
                invalid = True
            else:
                starts[identity] = (event, name, arguments, device is not None)
            if name == "read" and isinstance(event.get("args"), dict):
                path = event["args"].get("path")
                if isinstance(path, str):
                    any_gui_guide |= any(
                        guide_matches(path, skill) for skill in ("computer-use", *SKILLS.values())
                    )
            continue
        started = starts.get(identity)
        if started is None or started[0]["toolName"] != name or identity in completed:
            if name not in allowed and name not in violations:
                violations.append(name)
            invalid = True
            continue
        call, name, arguments, device = started
        completed.add(identity)
        payload = event.get("result")
        if device and (
            not isinstance(payload, dict) or not device_matches(payload, name, arguments)
        ):
            if "write" not in violations:
                violations.append("write")
            failed_calls.append({"tool": "write", "tool_call_id": identity})
            continue
        if event.get("isError") or _tool_result_failed(payload):
            failed_calls.append({"tool": name, "tool_call_id": identity})
            continue
        content = payload.get("content") if isinstance(payload, dict) else None
        texts = (
            [
                item["text"]
                for item in content
                if isinstance(item, dict)
                and item.get("type") == "text"
                and isinstance(item.get("text"), str)
            ]
            if isinstance(content, list)
            else []
        )
        decoded = _native_payload(texts[0], name) if name in readers and len(texts) == 1 else None
        if _tool_result_failed(decoded):
            failed_calls.append({"tool": name, "tool_call_id": identity})
            continue
        if name == "read":
            path = call["args"].get("path")
            if not isinstance(path, str):
                invalid = True
                continue
            for name in (*SKILLS.values(), "computer-use"):
                expected_path = layout["root"] / name / "SKILL.md"
                if guide_matches(path, name):
                    any_gui_guide = True
                    if name in manifest["skills"]:
                        body = expected_path.read_text().split("---", 2)[-1].strip()
                        if _hash(expected_path.read_bytes()) == manifest["skills"][name]["files"][
                            "SKILL.md"
                        ] and any(body in text for text in texts):
                            loaded.append(name)
        elif name == readers[0] and len(texts) == 1:
            if isinstance(decoded, dict) and _capability_agrees(
                decoded, manifest, detail=bool(arguments.get("detail"))
            ):
                invoked.append(name)
        elif name == readers[1] and _tool_result_succeeded(decoded):
            invoked.append(name)
    passed = (
        not failed_calls
        and not violations
        and (
            not any_gui_guide and not attempted
            if trigger == "negative"
            else expected in loaded and bool(invoked) and not runtime_before_guide
        )
    )
    incomplete = list(starts.keys() - completed)
    outcome = (
        "FAIL"
        if violations
        or failed_calls
        or runtime_before_guide
        or trigger == "negative"
        and (any_gui_guide or attempted)
        else "NOT_RUN"
        if invalid or incomplete or exit_code
        else "PASS"
        if passed
        else "FAIL"
    )
    return {
        "case": trigger,
        "status": outcome,
        "loaded": loaded,
        "invoked": invoked,
        "attempted": attempted,
        "failed_calls": failed_calls,
        "read_only_violations": violations,
        "incomplete_calls": incomplete,
        "invalid_inventory": invalid,
        "runtime_before_guide": runtime_before_guide,
        "load_before_invoke": bool(invoked) and not runtime_before_guide,
        "stages": _model_stages(loaded, invoked, bool(failed_calls)),
    }


def _verify_omp(
    layout: dict, manifest: dict, executable: str, cwd: Path, result: dict, trigger: str
) -> dict:
    # OMP distributes its real SDK source with the executable. Verify that provenance,
    # then use the native discovery, skill-prompt loader and MCP manager in one fresh process.
    package = Path(executable).resolve().parent.parent
    descriptor = package / "package.json"
    if (
        not descriptor.is_file()
        or json.loads(descriptor.read_text()).get("name") != "@oh-my-pi/pi-coding-agent"
    ):
        result["reason"] = (
            "installed OMP does not expose its validated SDK source; "
            "native trace adapter unavailable"
        )
        return result
    bun = shutil.which("bun")
    if not bun:
        result["reason"] = "OMP SDK verification requires the installed Bun launcher"
        return result
    skills_module = package / "src/extensibility/skills.ts"
    config_module = package / "src/mcp/config.ts"
    manager_module = package / "src/mcp/manager.ts"
    settings_module = package / "src/config/settings.ts"
    approval_module = package / "src/tools/settings.ts"
    settings = {}
    for suffix in ("config.yml", "config.yaml"):
        path = layout["config"].parent / suffix
        if path.is_file():
            settings = read_config("hermes", path.read_text())
            break
    options = {
        **(settings.get("skills") or {}),
        "cwd": str(cwd),
        "disabledExtensions": settings.get("disabledExtensions", []),
    }
    native_result = layout["state"] / "verification-native-results.json"
    _safe(native_result)
    atomic_write(native_result, "")
    script = f"""
import {{loadSkills, buildSkillPromptMessage}} from {json.dumps(str(skills_module))};
import {{loadAllMCPConfigs}} from {json.dumps(str(config_module))};
import {{MCPManager}} from {json.dumps(str(manager_module))};
import {{Settings}} from {json.dumps(str(settings_module))};
import {{cfgToolsApproval}} from {json.dumps(str(approval_module))};
const nativeSettings = await Settings.loadReadOnly({{cwd:{json.dumps(str(cwd))}}});
const nativeRoot = nativeSettings.getAgentDir();
if (!(await Bun.file(nativeRoot+'/config.yml').exists()) &&
    !(await Bun.file(nativeRoot+'/config.yaml').exists()) &&
    ((await Bun.file(nativeRoot+'/settings.json').exists()) ||
     (await Bun.file(nativeRoot+'/agent.db').exists())))
 throw new Error('native legacy-only settings require migration outside read-only verification');
const evidence = {{approval:cfgToolsApproval.get(nativeSettings)}};
const names = {json.dumps(list(manifest["skills"]))};
const found = await loadSkills({json.dumps(options)});
const selected = found.skills.filter(s => names.includes(s.name));
const loaded = [];
for (const skill of selected) {{
 const prompt = await buildSkillPromptMessage(skill, {{args:''}}, 'user');
 const content = await Bun.file(skill.filePath).text();
 const sha256 = new Bun.CryptoHasher('sha256').update(content).digest('hex');
 loaded.push({{name:skill.name,path:skill.filePath,sha256,lineCount:prompt.details.lineCount,
   contentLoaded:prompt.message.includes(content.split('---').slice(2).join('---').trim())}});
}}
evidence.discovery = {{selected,loaded}};
await Bun.write(process.env.CLEF_OMP_NATIVE_RESULT, JSON.stringify(evidence));
const configs = await loadAllMCPConfigs({json.dumps(str(cwd))});
const config = configs.configs['clef-use'];
if (!config) throw new Error('selected profile did not discover clef-use MCP');
const manager = new MCPManager({json.dumps(str(cwd))});
try {{
 await manager.connectServers({{'clef-use':config}}, {{'clef-use':configs.sources['clef-use']}});
 await manager.waitForPendingConnections();
 const tools=manager.getTools();
 const tool=tools.find(t=>t.mcpServerName==='clef-use' && t.mcpToolName==='computer_capabilities');
 if (!tool) throw new Error('native MCP manager did not discover computer_capabilities');
 const response=await tool.execute('clef-read-only-verification',{{}},undefined,{{}});
 evidence.invoked = {{tool:tool.name,result:response}};
 await Bun.write(process.env.CLEF_OMP_NATIVE_RESULT, JSON.stringify(evidence));
}} finally {{ await manager.disconnectAll(); }}
"""
    environment = {
        **os.environ,
        "CLEF_USE_MCP_READ_ONLY": "1",
        "CLEF_OMP_NATIVE_RESULT": str(native_result),
    }
    run = subprocess.run(
        [bun, "-e", script],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
    )
    trace = layout["state"] / "verification-native-trace.txt"
    atomic_write(trace, run.stdout + run.stderr)
    result.update(
        trace=str(trace),
        exit_code=run.returncode,
        model_driven=False,
        method="installed native OMP SDK discovery/load/MCP invocation; no model task",
        native_results=str(native_result),
    )
    _safe(native_result)
    with native_result.open("rb") as stream:
        raw = stream.read(_HERMES_TRANSCRIPT_LIMIT + 1)
    if len(raw) > _HERMES_TRANSCRIPT_LIMIT:
        raise ValueError("native OMP evidence exceeds verification bound")
    evidence = json.loads(raw)
    discovery = evidence.get("discovery", {})
    matches = [
        skill["name"]
        for skill in discovery.get("selected", [])
        if str(Path(skill["filePath"]).resolve())
        == str((layout["root"] / skill["name"] / "SKILL.md").resolve())
    ]
    loaded = [
        skill["name"]
        for skill in discovery.get("loaded", [])
        if skill["name"] in matches
        and skill.get("contentLoaded")
        and skill.get("lineCount", 0) > 0
        and skill.get("sha256") == manifest["skills"][skill["name"]]["files"]["SKILL.md"]
    ]
    invoked = evidence.get("invoked", {})
    stages = result["stages"]
    stages["DISCOVERED"] = {
        "status": "PASS" if set(matches) == set(manifest["skills"]) else "FAIL",
        "skills": matches,
    }
    stages["LOADED"] = {
        "status": "PASS" if set(loaded) == set(manifest["skills"]) else "NOT_RUN",
        "skills": loaded,
    }
    succeeded = _tool_result_succeeded(invoked.get("result"))
    stages["INVOKED"] = {
        "status": "PASS"
        if succeeded
        else "FAIL"
        if _tool_result_failed(invoked.get("result"))
        else "NOT_RUN",
        "tools": [invoked["tool"]] if succeeded else [],
    }
    result["status"] = (
        "PASS"
        if all(stages[name]["status"] == "PASS" for name in ("DISCOVERED", "LOADED", "INVOKED"))
        else "FAIL"
        if _tool_result_failed(invoked.get("result"))
        else "NOT_RUN"
    )
    result["model_trigger_verification"] = {
        "status": "NOT_RUN",
        "reason": (
            "native adapter execution does not establish model-driven positive/negative triggering"
        ),
    }
    if run.returncode:
        result["status"] = "FAIL"
        result["reason"] = _probe_reason(run.stdout + run.stderr, run.returncode)
    if trigger != "native" and result["status"] == "PASS":
        policies = evidence.get("approval")
        if not isinstance(policies, dict):
            result["status"] = "NOT_RUN"
            result["reason"] = "native OMP approval policies unavailable; model not started"
            return result
        return _verify_omp_model(layout, manifest, executable, cwd, result, trigger, policies)
    return result


def status() -> dict:
    results = []
    for harness in HARNESSES:
        try:
            layout = _layout(harness)
            manifest = _load_manifest(layout)
            if not manifest:
                results.append({"harness": harness, "status": "NOT_INSTALLED"})
                continue
            modified = [
                name
                for name, item in manifest["skills"].items()
                if _digests(_files(layout["root"] / name))
                != _managed_hashes(layout, manifest, name)
            ]
            config = (_read(layout["config"]) or b"").decode()
            if server_entry(harness, config) != manifest["mcp_entry"]:
                modified.append("mcp_entry")
            disabled = _disabled(layout, config, list(manifest["skills"]))
            compatibility = _compatibility(manifest)
            results.append(
                {
                    "harness": harness,
                    "profile": layout["profile"],
                    "status": "MODIFIED"
                    if modified
                    else "DISABLED"
                    if disabled
                    else "INCOMPATIBLE"
                    if compatibility["status"] == "MISMATCH"
                    else "INSTALLED",
                    "modified": modified,
                    "disabled": disabled,
                    "release": manifest["release"],
                    "compatibility": compatibility,
                    "stages": _stages("FAIL" if modified else "PASS"),
                }
            )
        except (ValueError, OSError) as exc:
            results.append({"harness": harness, "status": "CONFLICT", "reason": str(exc)})
    return {"integrations": results}


def refresh_managed(
    command: str | None = None, *, previous_commands: list[str] | None = None
) -> dict:
    """Refresh only approvals recorded for the currently selected harness profiles.

    This never discovers/registers a new harness or guesses an inactive profile's HOME.
    Project-scoped approvals are intentionally refreshed from that project, not globally.
    """
    results = []

    def command_path(path: str | Path) -> str:
        # Do not resolve a captured current alias after activation has switched it.
        return os.path.normcase(os.path.normpath(str(Path(path).absolute())))

    previous = (
        {command_path(path) for path in previous_commands}
        if previous_commands is not None
        else None
    )
    selected = command_path(command) if command is not None else None
    owner = None
    if selected is not None and previous is None:
        # Installed CLI entrypoints have authoritative release receipts even
        # when an older updater did not pass a pre-activation snapshot. POSIX
        # public shell aliases require the running venv's sibling executable.
        native_name = "clef-use.exe" if os.name == "nt" else "clef-use"
        for binary in (
            Path(command).resolve(),
            Path(sys.executable).with_name(native_name).resolve(),
        ):
            release = binary.parent.parent
            if release.parent.name != "versions":
                continue
            raw = _read(release / "installed.json")
            receipt = json.loads(raw) if raw else None
            launcher = receipt.get("launcher") if isinstance(receipt, dict) else None
            if not isinstance(launcher, str) or not Path(launcher).is_absolute():
                continue
            if selected in {command_path(binary), command_path(launcher)}:
                owner = (command_path(launcher), release.parent, binary.parent.name, binary.name)
                break

    def owned_command(recorded: str) -> bool:
        normalized = command_path(recorded)
        if previous is not None:
            return normalized in previous
        if selected is None or normalized == selected:
            return True
        if owner is None:
            return False
        launcher, versions, directory, name = owner
        if normalized == launcher:
            return True
        binary = Path(recorded).resolve()
        if (
            binary.name != name
            or binary.parent.name != directory
            or binary.parent.parent.parent != versions
        ):
            return False
        raw = _read(binary.parent.parent / "installed.json")
        receipt = json.loads(raw) if raw else None
        prior_launcher = receipt.get("launcher") if isinstance(receipt, dict) else None
        return (
            isinstance(prior_launcher, str)
            and Path(prior_launcher).is_absolute()
            and command_path(prior_launcher) == launcher
        )

    for harness in HARNESSES:
        try:
            layout = _layout(harness)
            if not (layout["state"] / "manifest.json").exists():
                continue
            with _locked(layout):
                _recover(layout)
                manifest = _load_manifest(layout)
                if not manifest:
                    continue
                recorded_command = (manifest.get("mcp_entry") or {}).get("command")
                if not isinstance(recorded_command, str) or not owned_command(recorded_command):
                    continue
                selected_command = command or recorded_command
                result = _integrate(layout, manifest["selection"], False, selected_command, True)
            results.append({"harness": harness, **result})
        except (ValueError, OSError) as exc:
            results.append({"harness": harness, "status": "CONFLICT", "reason": str(exc)})
    return {
        "status": "REFRESHED"
        if all(item["status"] in ("INSTALLED", "UNCHANGED") for item in results)
        else "PARTIAL",
        "integrations": results,
        "scope": "approved current profiles for prior executables or the selected installation",
    }


def remove(
    harness: str, dry_run: bool = False, scope: str = "user", project: Path | str | None = None
) -> dict:
    layout = _layout(harness, scope, project)
    if "status" in layout:
        return layout
    if not layout["state"].exists():
        return {"status": "NOT_INSTALLED"}
    with _locked(layout):
        if not dry_run:
            _recover(layout)
        approved = _metadata_inputs(layout)
        try:
            manifest = _load_manifest(layout)
            registry = _registry(layout)
        except (OSError, ValueError):
            conflict = _validate_preconditions(approved, {})
            if conflict:
                return conflict
            raise
        conflict = _validate_preconditions(approved, {})
        if conflict:
            return conflict
        if not manifest:
            return {"status": "NOT_INSTALLED"}
        writes = {}
        preserved = []
        remaining = dict(manifest["skills"])
        deleted = []
        inventories = {}
        for name in manifest["skills"]:
            existing = _files(layout["root"] / name)
            inventories[layout["root"] / name] = existing
            if _digests(existing) != _managed_hashes(layout, manifest, name, registry):
                preserved.append(name)
                continue
            managed = _managed_hashes(layout, manifest, name, registry)
            if _release_guide(layout, registry, name):
                for relative in managed:
                    writes[layout["root"] / name / relative] = None
                deleted.append(name)
            del remaining[name]
        config_raw = _read(layout["config"])
        approved[layout["config"]] = config_raw
        config = (config_raw or b"").decode()
        if manifest["owns_mcp"]:
            if server_entry(harness, config) == manifest["mcp_entry"]:
                writes[layout["config"]] = render_entry(
                    harness, config, manifest["previous_mcp_entry"]
                ).encode()
            else:
                preserved.append("mcp_entry")
        if preserved:
            entry_removed = layout["config"] in writes
            updated = {
                **manifest,
                "skills": remaining,
                "mcp_entry": manifest["previous_mcp_entry"]
                if entry_removed
                else manifest["mcp_entry"],
                "owns_mcp": False if entry_removed else manifest["owns_mcp"],
            }
            writes[layout["state"] / "manifest.json"] = (
                json.dumps(updated, indent=2) + "\n"
            ).encode()
        else:
            writes[layout["state"] / "manifest.json"] = None
        if layout.get("registry"):
            writes[layout["registry"]] = (
                (json.dumps(registry, indent=2) + "\n").encode() if registry["skills"] else None
            )
        for directory, files in inventories.items():
            for path in writes:
                if path.is_relative_to(directory):
                    approved[path] = files.get(path.relative_to(directory).as_posix())
        conflict = _validate_preconditions(approved, inventories)
        if conflict:
            return conflict
        if not dry_run:
            conflict = _transaction(layout, writes, approved, inventories)
            if conflict:
                return conflict
            for name in deleted:
                directory = layout["root"] / name
                for child in sorted(directory.rglob("*"), reverse=True):
                    if child.is_dir():
                        child.rmdir()
                directory.rmdir()
        return {
            "status": "PREVIEW" if dry_run else "PARTIAL" if preserved else "REMOVED",
            "preserved": preserved,
            "changed": [str(path) for path in writes],
        }


def _rpc(executable: str, method: str, params: dict, cwd: Path) -> dict:
    """Call the real Codex app server, never an imitated skill scanner."""
    process = subprocess.Popen(
        [executable, "app-server", "--stdio"],
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    messages = queue.Queue()

    def reader():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except json.JSONDecodeError:
                continue

    threading.Thread(target=reader, daemon=True).start()

    def send(data):
        process.stdin.write(json.dumps(data) + "\n")
        process.stdin.flush()

    def response(identifier):
        while True:
            value = messages.get(timeout=30)
            if value.get("id") == identifier:
                if "error" in value:
                    raise ValueError(str(value["error"]))
                return value["result"]

    try:
        send(
            {
                "id": 1,
                "method": "initialize",
                "params": {"clientInfo": {"name": "clef_use_verification", "version": "1"}},
            }
        )
        response(1)
        send({"method": "initialized"})
        send({"id": 2, "method": method, "params": params})
        return response(2)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def _codex_guide_path_in_command(path: str, command: str) -> bool:
    if PureWindowsPath(path).drive:
        # Native Codex traces can shell-escape Windows separators twice.
        path = re.sub(r"\\+", "/", path).casefold()
        command = re.sub(r"\\+", "/", command).casefold()
    return re.search(rf"(?:^|[\s\"']){re.escape(path)}(?=$|[\s\"'])", command) is not None


def _codex_executor_failures(stderr: str, guides: dict[str, str]) -> list[dict]:
    failures = []
    for line in stderr.splitlines():
        match = re.match(
            r"^\d{4}-\d{2}-\d{2}T\S+ +ERROR codex_core::tools::router: "
            r"error=exec_command failed for `(.+)`: CreateProcess \{ message:.*?"
            r"Failed to create unified exec process: timed out after (\d+)ms "
            r"connecting runner (pipe-in|pipe-out)",
            line,
        )
        if match:
            failures.append(
                {
                    "code": "NATIVE_EXECUTOR_STARTUP_TIMEOUT",
                    "phase": match[3],
                    "timeout_ms": int(match[2]),
                    "selected_guide_attempt": any(
                        _codex_guide_path_in_command(path, match[1]) for path in guides.values()
                    ),
                    "evidence_sha256": _hash(line.encode()),
                }
            )
    return failures


def _codex_mcp_configuration(executable: str, cwd: Path, config_args: tuple = ()) -> dict:
    argv = [executable, *config_args, "-C", str(cwd)]
    run = subprocess.run(
        [*argv, "mcp", "list", "--json"],
        stdin=subprocess.DEVNULL,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if run.returncode:
        # Native diagnostics can contain transport credentials. Keep them out of results.
        raise ValueError(f"native Codex MCP configuration failed (exit {run.returncode})")
    servers = json.loads(run.stdout)
    if not isinstance(servers, list):
        raise ValueError("native Codex MCP configuration is not a server list")
    catalog = {}
    for server in servers:
        if (
            not isinstance(server, dict)
            or not isinstance(server.get("name"), str)
            or not server["name"]
            or server["name"] in catalog
            or not isinstance(server.get("enabled"), bool)
            or not isinstance(server.get("transport"), dict)
        ):
            raise ValueError("native Codex MCP configuration has an invalid server")
        catalog[server["name"]] = server
    return catalog


@contextmanager
def _codex_verification_profile(executable: str, cwd: Path, entry: dict):
    if entry.get("enabled", True) is not True:
        raise ValueError("disabled managed Codex MCP entry is preserved")
    servers = {}
    for name, server in _codex_mcp_configuration(executable, cwd).items():
        if name == "clef-use":
            continue
        transport = server["transport"]
        # Disabled entries still require a valid native transport in profile files.
        if isinstance(transport.get("command"), str):
            transport = {"command": transport["command"], "args": transport.get("args") or []}
        elif isinstance(transport.get("url"), str):
            transport = {"url": transport["url"]}
        else:
            raise ValueError("native Codex MCP transport cannot be disabled safely")
        servers[name] = {**transport, "enabled": False}
    environment = {**entry.get("env", {}), "CLEF_USE_MCP_READ_ONLY": "1"}
    servers["clef-use"] = {
        **entry,
        "enabled": True,
        "enabled_tools": ["computer_capabilities", "computer_status"],
        "env": environment,
    }
    directory = target_path("codex").parent
    _safe(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = tomlkit.dumps({"mcp_servers": servers}).encode("utf-8")
    fd, filename = tempfile.mkstemp(
        prefix="clef-use-verification-", suffix=".config.toml", dir=directory
    )
    path = Path(filename)
    profile = path.name.removesuffix(".config.toml")
    # Trusted project layers outrank profiles. Override only scope controls at
    # CLI priority; approved transport values stay in the private profile.
    controls = tomlkit.inline_table()
    for name in servers:
        controls[name] = {"enabled": False}
    controls["clef-use"] = {
        "enabled": True,
        "enabled_tools": ["computer_capabilities", "computer_status"],
        "env": {"CLEF_USE_MCP_READ_ONLY": "1"},
    }
    config_args = ("-p", profile, "-c", "mcp_servers=" + controls.as_string())
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        actual = _codex_mcp_configuration(executable, cwd, config_args)
        selected = actual.get("clef-use", {})
        transport = selected.get("transport", {})
        if (
            not selected.get("enabled")
            or any(server["enabled"] for name, server in actual.items() if name != "clef-use")
            or transport.get("command") != entry.get("command")
            or transport.get("args") != entry.get("args", [])
            or transport.get("env") != environment
            or (transport.get("env_vars") or []) != (entry.get("env_vars") or [])
            or transport.get("cwd") != entry.get("cwd")
        ):
            raise ValueError("native Codex read-only profile does not match approved scope")
        yield config_args
    finally:
        if _read(path) != data:
            raise ValueError("modified temporary Codex profile preserved")
        path.unlink()


def verify(
    harness: str,
    live: bool = False,
    read_only: bool = True,
    scope: str = "user",
    project: Path | str | None = None,
    trigger: str = "natural",
) -> dict:
    if not read_only:
        raise ValueError("GUI task verification requires a separately opted-in isolated fixture")
    if trigger not in ("natural", "explicit", "negative", "native"):
        raise ValueError("trigger must be natural, explicit, negative or native")
    layout = _layout(harness, scope, project)
    if "status" in layout:
        return layout
    if not _load_manifest(layout):
        return _verify_selected(layout, harness, live, project, trigger)
    with _locked(layout):
        return _verify_selected(layout, harness, live, project, trigger)


def _verify_selected(
    layout: dict, harness: str, live: bool, project: Path | str | None, trigger: str
) -> dict:
    manifest = _load_manifest(layout)
    stages = _stages()
    result = {
        "harness": harness,
        "profile": layout["profile"],
        "stages": stages,
        "status": "NOT_RUN",
        "read_only": True,
    }
    if not manifest:
        result["reason"] = "no managed integration for selected profile/scope"
        return result
    modified = [
        name
        for name, item in manifest["skills"].items()
        if _digests(_files(layout["root"] / name)) != _managed_hashes(layout, manifest, name)
    ]
    stages["INSTALLED"] = {"status": "FAIL" if modified else "PASS", "modified": modified}
    if modified:
        result["status"] = "FAIL"
        return result
    config = (_read(layout["config"]) or b"").decode()
    if server_entry(harness, config) != manifest.get("mcp_entry"):
        result.update(
            status="FAIL", reason="managed MCP entry was modified; no harness invocation attempted"
        )
        return result
    disabled = _disabled(layout, config, list(manifest["skills"]))
    if disabled:
        result.update(status="FAIL", reason="explicit disabled skills preserved", disabled=disabled)
        return result
    compatibility = _compatibility(manifest)
    result["compatibility"] = compatibility
    if compatibility["status"] != "MATCH":
        result.update(status="FAIL", reason=compatibility["action"])
        return result
    if not live:
        result["reason"] = "actual harness not executed; use --live --read-only"
        return result
    executable = shutil.which(harness)
    if not executable:
        result["reason"] = "harness executable is unavailable"
        return result
    cwd = Path(project or manifest.get("project") or Path.cwd())
    try:
        result["stages"]["TASK_VERIFIED"]["reason"] = (
            "read-only verification does not execute a GUI fixture"
        )
        if harness == "hermes":
            return _verify_hermes(layout, manifest, executable, cwd, result, trigger)
        if harness == "omp":
            return _verify_omp(layout, manifest, executable, cwd, result, trigger)
        listed = _rpc(executable, "skills/list", {"cwds": [str(cwd)], "forceReload": True}, cwd)
        found = [
            skill
            for group in listed.get("data", [])
            for skill in group.get("skills", [])
            if skill.get("name") in manifest["skills"]
        ]
        expected = {
            name: str((layout["root"] / name / "SKILL.md").resolve()) for name in manifest["skills"]
        }
        matches = {
            skill["name"]
            for skill in found
            if skill.get("enabled")
            and str(Path(skill["path"]).resolve()) == expected[skill["name"]]
            and sum(
                candidate["name"] == skill["name"] and candidate.get("enabled")
                for candidate in found
            )
            == 1
        }
        stages["DISCOVERED"] = {
            "status": "PASS" if matches == set(expected) else "FAIL",
            "skills": found,
        }
        if matches != set(expected):
            result["status"] = "FAIL"
            return result
        if trigger == "native":
            result["reason"] = (
                "native Codex skill discovery passed; model body load/invocation not executed"
            )
            return result
        # Only the two read-only runtime tools may be invoked during this fresh session.
        argv = [
            executable,
            "exec",
            "--json",
            "--ephemeral",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "-C",
            str(cwd),
        ]
        trace = layout["state"] / f"verification-{trigger}-trace.jsonl"
        with _codex_verification_profile(executable, cwd, manifest["mcp_entry"]) as config_args:
            argv.extend([*config_args, _verification_prompt(trigger)])
            run = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
                cwd=cwd,
                env={**os.environ, "CLEF_USE_MCP_READ_ONLY": "1"},
            )
            atomic_write(trace, run.stdout)
            atomic_write(trace.with_suffix(".stderr"), run.stderr)
            result["trace"] = str(trace)
            result["stderr_trace"] = str(trace.with_suffix(".stderr"))
            result["exit_code"] = run.returncode
        events = []
        for line in run.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        loaded = []
        observed_guide_bodies = []
        invoked = []
        attempted = []
        failed = False
        executor_failures = _codex_executor_failures(run.stderr, expected)
        any_gui_guide = any(error["selected_guide_attempt"] for error in executor_failures)
        selected = (
            "clef-use-blender"
            if trigger == "natural" and "clef-use-blender" in expected
            else "clef-use"
        )
        runtime_before_guide = False
        observed_body_before_invoke = True
        capability_catalog = None
        guide_resources = {f"clef-use://guides/{name}/SKILL.md": name for name in expected}
        for event in events:
            item = event.get("item", {})
            arguments = item.get("arguments")
            arguments = arguments if isinstance(arguments, dict) else {}
            uri = arguments.get("uri")
            selected_resource = (
                item.get("type") == "mcp_tool_call"
                and item.get("tool") == "read_mcp_resource"
                and isinstance(uri, str)
                and (uri == "clef-use://api/schema" or uri.startswith("clef-use://guides/"))
            )
            selected_tool = (
                item.get("type") == "mcp_tool_call"
                and item.get("server") == "clef-use"
                and item.get("tool") in ("computer_capabilities", "computer_status")
            )
            if (selected_tool or selected_resource) and event.get("type") in (
                "item.started",
                "item.updated",
                "item.completed",
            ):
                if item["tool"] not in attempted:
                    attempted.append(item["tool"])
                if selected_tool and selected not in loaded:
                    runtime_before_guide = True
                if selected_tool and selected not in observed_guide_bodies:
                    observed_body_before_invoke = False
            if event.get("type") != "item.completed":
                continue
            if item.get("type") == "command_execution" and item.get("exit_code") == 0:
                output = item.get("aggregated_output", "")
                any_gui_guide |= bool(
                    re.search(
                        r"[\\/]+(?:clef-use(?:-blender|-diagnostics)?|computer-use)[\\/]+SKILL.md",
                        item.get("command", ""),
                        re.IGNORECASE,
                    )
                )
                for name in expected:
                    body = (layout["root"] / name / "SKILL.md").read_text(encoding="utf-8")
                    if body.strip() in output and name not in observed_guide_bodies:
                        observed_guide_bodies.append(name)
                    if (
                        _codex_guide_path_in_command(expected[name], item.get("command", ""))
                        and body.strip() in output
                    ):
                        loaded.append(name)
            if selected_tool or selected_resource:
                call_failed = (
                    item.get("status") == "failed"
                    or bool(item.get("error"))
                    or _tool_result_failed(item.get("result"))
                )
                failed |= call_failed
            if selected_resource and not call_failed and item.get("status") == "completed":
                payload = item.get("result")
                blocks = payload.get("content", []) if isinstance(payload, dict) else []
                for block in blocks if isinstance(blocks, list) else []:
                    if not isinstance(block, dict) or block.get("type") != "text":
                        continue
                    try:
                        resource = json.loads(block.get("text", ""))
                    except (TypeError, json.JSONDecodeError):
                        continue
                    if (
                        not isinstance(resource, dict)
                        or item.get("server") != "clef-use"
                        or arguments.get("server") != "clef-use"
                        or resource.get("server") != "clef-use"
                        or resource.get("uri") != uri
                        or uri not in guide_resources
                        or not isinstance(resource.get("contents"), list)
                    ):
                        continue
                    name = guide_resources[uri]
                    body = (layout["root"] / name / "SKILL.md").read_text(encoding="utf-8")
                    if (
                        any(
                            isinstance(content, dict)
                            and content.get("uri") == uri
                            and content.get("text") == body
                            for content in resource["contents"]
                        )
                        and name not in loaded
                    ):
                        loaded.append(name)
            if selected_tool:
                if (
                    item.get("status") == "completed"
                    and not item.get("error")
                    and _tool_result_succeeded(item.get("result"))
                ):
                    if item["tool"] == "computer_capabilities":
                        payload = item["result"]
                        blocks = payload.get("content", [])
                        texts = [
                            block.get("text")
                            for block in (blocks if isinstance(blocks, list) else [])
                            if isinstance(block, dict) and block.get("type") == "text"
                        ]
                        decoded = (
                            _native_payload(texts[0], item["tool"])
                            if len(texts) == 1 and isinstance(texts[0], str)
                            else None
                        )
                        if not isinstance(decoded, dict) or _tool_result_failed(decoded):
                            failed = True
                            continue
                        operation_id = arguments.get("operation_id")
                        if operation_id is not None:
                            from .capabilities import digest

                            operations = (
                                capability_catalog.get("operations", [])
                                if capability_catalog is not None
                                else []
                            )
                            matches = [
                                operation
                                for operation in (
                                    operations if isinstance(operations, list) else []
                                )
                                if isinstance(operation, dict)
                                and operation.get("family") == operation_id
                            ]
                            if len(matches) != 1 or digest(decoded) != digest(matches[0]):
                                failed = True
                                continue
                        else:
                            if decoded.get(
                                "read_only_facade"
                            ) is not True or not _capability_agrees(
                                decoded, manifest, detail=arguments.get("detail") is True
                            ):
                                failed = True
                                continue
                            capability_catalog = decoded
                    invoked.append(item["tool"])
        load_before_invoke = bool(invoked) and not runtime_before_guide
        stages.update(_model_stages(loaded, invoked, failed))
        stages["TASK_VERIFIED"]["reason"] = "read-only verification does not execute a GUI fixture"
        passed = (
            not any_gui_guide and not attempted
            if trigger == "negative"
            else selected in loaded
            and bool(invoked)
            and load_before_invoke
            and capability_catalog is not None
        )
        violation = (
            failed
            or bool(executor_failures)
            or runtime_before_guide
            or (trigger == "negative" and (any_gui_guide or attempted))
        )
        outcome = (
            "FAIL"
            if violation
            else "PASS"
            if passed and not run.returncode
            else "NOT_RUN"
            if run.returncode
            else "FAIL"
        )
        result.update(status=outcome, model_driven=True)
        result["model_trigger_verification"] = {
            "case": trigger,
            "status": outcome,
            "loaded": loaded,
            "observed_guide_bodies": observed_guide_bodies,
            "observed_body_before_invoke": bool(invoked) and observed_body_before_invoke,
            "invoked": invoked,
            "attempted": attempted,
            "load_before_invoke": load_before_invoke,
            "runtime_before_guide": runtime_before_guide,
            "capability_catalog_verified": capability_catalog is not None,
            "native_executor_failures": executor_failures,
            "stages": _model_stages(loaded, invoked, failed),
        }
        if executor_failures:
            result["reason_code"] = "NATIVE_EXECUTOR_STARTUP_TIMEOUT"
            result["reason"] = (
                "native command executor failed before command start; inspect private stderr trace"
            )
        elif run.returncode:
            result["reason"] = _probe_reason(run.stdout + run.stderr, run.returncode)
        elif selected in observed_guide_bodies and selected not in loaded:
            result["reason_code"] = "GUIDE_ORIGIN_NOT_VERIFIED"
            result["reason"] = (
                "complete selected guide body observed; command trace does not prove "
                "the installed file origin. Invocation before verified load is not "
                "proof of invocation before an actual read"
            )
    except (OSError, ValueError, queue.Empty, subprocess.TimeoutExpired) as exc:
        result["reason"] = f"actual harness verification failed: {type(exc).__name__}: {exc}"
    return result

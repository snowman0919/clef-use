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
import threading
from contextlib import ExitStack, contextmanager
from pathlib import Path, PureWindowsPath

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
config = load_config()['mcp_servers']['clef-use']
try:
    names = register_mcp_servers({'clef-use':config})
    name = mcp_prefixed_tool_name('clef-use','computer_capabilities')
    if name not in names: raise RuntimeError('native registry did not discover capability tool')
    tool = registry.get_entry(name)
    payload = tool.handler({})
    if isinstance(payload,str): payload = json.loads(payload)
    print('CLEF_INVOKED:' + json.dumps({'tool':name,'result':payload}))
finally:
    shutdown_mcp_servers()
""".replace("__NAMES__", repr(list(manifest["skills"])))
    path = layout["state"] / "verification-hermes-native.py"
    atomic_write(path, script)
    try:
        # Ask this installed launcher for its exact isolated interpreter/bootstrap.
        # Replace only the fixed entrypoint with our private native-library probe.
        launch = subprocess.run(
            [executable, "--print-runtime-command"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if launch.returncode:
            raise ValueError("installed Hermes launcher cannot advertise its runtime command")
        command = json.loads(launch.stdout)
        if not isinstance(command, list) or len(command) < 4 or command[1:3] != ["-I", "-c"]:
            raise ValueError("unsupported Hermes runtime command; native adapter not executed")
        bootstrap = ast.parse(command[3])
        call = bootstrap.body[-1]
        if (
            not isinstance(call, ast.Expr)
            or not isinstance(call.value, ast.Call)
            or not isinstance(call.value.func, ast.Attribute)
            or call.value.func.attr != "run_module"
        ):
            raise ValueError("Hermes bootstrap entrypoint differs; native adapter not executed")
        bootstrap.body[-1] = ast.parse(f"runpy.run_path({str(path)!r}, run_name='__main__')").body[
            0
        ]
        command[3] = ast.unparse(bootstrap)
        run = subprocess.run(
            command,
            cwd=cwd,
            env={**os.environ, "CLEF_USE_MCP_READ_ONLY": "1"},
            capture_output=True,
            text=True,
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
    )
    result["status"] = (
        "PASS"
        if loaded and succeeded
        else "FAIL"
        if _tool_result_failed(invoked.get("result"))
        else "NOT_RUN"
    )
    if run.returncode:
        result["native_reason"] = _probe_reason(run.stdout + run.stderr, run.returncode)
    return result


def _verify_hermes(
    layout: dict, manifest: dict, executable: str, cwd: Path, result: dict, trigger: str
) -> dict:
    result = _hermes_native(layout, manifest, executable, cwd, result)
    if trigger == "native":
        return result
    environment = {**os.environ, "CLEF_USE_MCP_READ_ONLY": "1", "NO_COLOR": "1", "COLUMNS": "200"}
    listed = subprocess.run(
        [executable, "skills", "list", "--enabled-only", "--source", "local"],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
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
        [
            executable,
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
        timeout=120,
    )
    events = _jsonlines(run.stdout)
    trace = layout["state"] / f"verification-{trigger}-trace.jsonl"
    atomic_write(trace, run.stdout)
    atomic_write(trace.with_suffix(".stderr"), run.stderr)
    result.update(trace=str(trace), exit_code=run.returncode, model_driven=True)
    loaded = []
    invoked = []
    attempted = []
    failed = False
    calls = {}
    for event in events:
        selected_tool = event.get("name") in (
            "mcp__clef_use__computer_capabilities",
            "mcp__clef_use__computer_status",
        )
        if selected_tool and event.get("type") in ("tool_use", "tool_result"):
            if event["name"] not in attempted:
                attempted.append(event["name"])
            failed |= event.get("type") == "tool_result" and bool(event.get("is_error"))
        key = event.get("tool_call_id", event.get("name"))
        if event.get("type") == "tool_use":
            calls.setdefault(key, []).append(event)
            continue
        if event.get("type") != "tool_result" or event.get("is_error"):
            continue
        pending = calls.get(key, [])
        call = pending.pop(0) if pending else {}
        if event.get("name") == "skill_view":
            try:
                payload = json.loads(event.get("output", ""))
            except json.JSONDecodeError:
                # Hermes caps tool outputs at 5000 characters. A successful body-read
                # prefix plus the exact native catalog provenance proves a load,
                # while a name echo or a file-existence check never does.
                name = call.get("input", {}).get("name")
                output = event.get("output", "")
                if (
                    name in manifest["skills"]
                    and not call.get("input", {}).get("file_path")
                    and '"success": true' in output
                    and _body_prefix_in_output(layout["root"] / name / "SKILL.md", output)
                    and result["stages"]["LOADED"]["status"] == "PASS"
                ):
                    loaded.append(name)
                continue
            name = call.get("input", {}).get("name")
            expected = str((layout["root"] / str(name) / "SKILL.md").resolve())
            if (
                name in manifest["skills"]
                and payload.get("success")
                and payload.get("_source_path") == expected
                and payload.get("content")
            ):
                loaded.append(name)
        if selected_tool:
            try:
                payload = json.loads(event.get("output", ""))
            except json.JSONDecodeError:
                continue
            failed |= _tool_result_failed(payload)
            if _tool_result_succeeded(payload):
                invoked.append(event["name"])
    expected = (
        "clef-use-blender"
        if trigger == "natural" and "clef-use-blender" in manifest["skills"]
        else "clef-use"
    )
    any_gui_guide = any(
        event.get("type") == "tool_use"
        and event.get("name") == "skill_view"
        and event.get("input", {}).get("name") in ("computer-use", *SKILLS.values())
        for event in events
    )
    passed = (
        not any_gui_guide and not attempted
        if trigger == "negative"
        else expected in loaded and bool(invoked)
    )
    result["model_trigger_verification"] = {
        "case": trigger,
        "status": "PASS"
        if passed and run.returncode == 0
        else "NOT_RUN"
        if run.returncode
        else "FAIL",
        "loaded": loaded,
        "invoked": invoked,
        "attempted": attempted,
        "stages": _model_stages(loaded, invoked, failed),
    }
    if result["model_trigger_verification"]["status"] == "FAIL":
        result["status"] = "FAIL"
    elif result["model_trigger_verification"]["status"] == "NOT_RUN":
        result["status"] = "NOT_RUN"
    if run.returncode:
        result["reason"] = _probe_reason(run.stdout + run.stderr, run.returncode)
    return result


def _body_prefix_in_output(path: Path, output: str) -> bool:
    """Recognize actual guide text when a harness truncates its JSON tool result."""
    source = path.read_text()
    heading = source.find("\n# ")
    if heading < 0:
        return False
    # Include frontmatter and body, rather than accepting a skill name echo.
    prefix = source[: heading + 180]
    escaped = json.dumps(prefix, ensure_ascii=False)[1:-1]
    # Hermes stream-json may escape the rendered content before serializing it.
    twice = json.dumps(escaped, ensure_ascii=False)[1:-1]
    return f'"content": "{escaped}' in output or f'"content": "{twice}' in output


def _model_stages(loaded: list[str], invoked: list[str], failed: bool) -> dict:
    return {
        "LOADED": {"status": "PASS" if loaded else "NOT_RUN", "skills": loaded},
        "INVOKED": {
            "status": "PASS" if invoked else "FAIL" if failed else "NOT_RUN",
            "tools": invoked,
        },
    }


def _verify_omp_model(
    layout: dict, manifest: dict, executable: str, cwd: Path, result: dict, trigger: str
) -> dict:
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
        timeout=120,
    )
    trace = layout["state"] / f"verification-{trigger}-trace.jsonl"
    atomic_write(trace, run.stdout + run.stderr)
    events = _jsonlines(run.stdout)
    starts = {
        event.get("toolCallId"): event
        for event in events
        if event.get("type") == "tool_execution_start"
    }
    loaded, invoked = [], []
    attempted = []
    failed = False
    any_gui_guide = False
    for event in events:
        selected_tool = event.get("toolName") in (
            "mcp__clef_use_computer_capabilities",
            "mcp__clef_use_computer_status",
        )
        if selected_tool and event.get("type") in ("tool_execution_start", "tool_execution_end"):
            if event["toolName"] not in attempted:
                attempted.append(event["toolName"])
            failed |= event.get("type") == "tool_execution_end" and bool(event.get("isError"))
        if event.get("type") != "tool_execution_end" or event.get("isError"):
            continue
        call = starts.get(event.get("toolCallId"), {})
        arguments = call.get("args", {})
        path = arguments.get("path", "")
        content = json.dumps(event.get("result", {}))
        if event.get("toolName") == "read":
            for name in (*SKILLS.values(), "computer-use"):
                expected_path = layout["root"] / name / "SKILL.md"
                if path == f"skill://{name}" or (
                    path and Path(path).resolve() == expected_path.resolve()
                ):
                    any_gui_guide = True
                    if name in manifest["skills"]:
                        body = expected_path.read_text().split("---", 2)[-1].strip()
                        prefix = json.dumps(body[:180], ensure_ascii=False)[1:-1]
                        if prefix in content:
                            loaded.append(name)
        if selected_tool:
            failed |= _tool_result_failed(event.get("result"))
            if _tool_result_succeeded(event.get("result")):
                invoked.append(event["toolName"])
    expected = (
        "clef-use-blender"
        if trigger == "natural" and "clef-use-blender" in manifest["skills"]
        else "clef-use"
    )
    passed = (
        not any_gui_guide and not attempted
        if trigger == "negative"
        else expected in loaded and bool(invoked)
    )
    outcome = "PASS" if passed and not run.returncode else "NOT_RUN" if run.returncode else "FAIL"
    result.update(trace=str(trace), model_driven=True, exit_code=run.returncode)
    result["model_trigger_verification"] = {
        "case": trigger,
        "status": outcome,
        "loaded": loaded,
        "invoked": invoked,
        "attempted": attempted,
        "stages": _model_stages(loaded, invoked, failed),
    }
    result["status"] = outcome
    if run.returncode:
        result["reason"] = _probe_reason(run.stdout + run.stderr, run.returncode)
    return result


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
    script = f"""
import {{loadSkills, buildSkillPromptMessage}} from {json.dumps(str(skills_module))};
import {{loadAllMCPConfigs}} from {json.dumps(str(config_module))};
import {{MCPManager}} from {json.dumps(str(manager_module))};
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
console.log('CLEF_DISCOVERY:' + JSON.stringify({{selected,loaded}}));
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
 console.log('CLEF_INVOKED:' + JSON.stringify({{tool:tool.name,result:response}}));
}} finally {{ await manager.disconnectAll(); }}
"""
    environment = {**os.environ, "CLEF_USE_MCP_READ_ONLY": "1"}
    run = subprocess.run(
        [bun, "-e", script], cwd=cwd, env=environment, capture_output=True, text=True, timeout=90
    )
    trace = layout["state"] / "verification-native-trace.txt"
    atomic_write(trace, run.stdout + run.stderr)
    result.update(
        trace=str(trace),
        exit_code=run.returncode,
        model_driven=False,
        method="installed native OMP SDK discovery/load/MCP invocation; no model task",
    )
    discovery = next(
        (
            json.loads(line.removeprefix("CLEF_DISCOVERY:"))
            for line in run.stdout.splitlines()
            if line.startswith("CLEF_DISCOVERY:")
        ),
        {},
    )
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
    invoked = next(
        (
            json.loads(line.removeprefix("CLEF_INVOKED:"))
            for line in run.stdout.splitlines()
            if line.startswith("CLEF_INVOKED:")
        ),
        {},
    )
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
        result["reason"] = _probe_reason(run.stdout + run.stderr, run.returncode)
    if trigger != "native" and result["status"] == "PASS":
        return _verify_omp_model(layout, manifest, executable, cwd, result, trigger)
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


def refresh_managed(command: str | None = None) -> dict:
    """Refresh only approvals recorded for the currently selected harness profiles.

    This never discovers/registers a new harness or guesses an inactive profile's HOME.
    Project-scoped approvals are intentionally refreshed from that project, not globally.
    """
    results = []
    for harness in HARNESSES:
        try:
            layout = _layout(harness)
            manifest = _load_manifest(layout)
            if not manifest:
                continue
            selected_command = command or (manifest.get("mcp_entry") or {}).get("command")
            result = integrate(
                harness,
                skills=manifest["selection"],
                command=selected_command,
                replace_managed_command=True,
            )
            results.append({"harness": harness, **result})
        except (ValueError, OSError) as exc:
            results.append({"harness": harness, "status": "CONFLICT", "reason": str(exc)})
    return {
        "status": "REFRESHED"
        if all(item["status"] in ("INSTALLED", "UNCHANGED") for item in results)
        else "PARTIAL",
        "integrations": results,
        "scope": "previously approved user integrations in currently selected profiles",
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


def _codex_verification_override(config: dict) -> str:
    # CLI dotted paths do not unquote key segments. Inline TOML preserves
    # arbitrary server names and merges these fields into existing transports.
    fields = [
        f"{json.dumps(server, ensure_ascii=False)}={{enabled=false}}"
        for server in config.get("mcp_servers", {})
        if server != "clef-use"
    ]
    fields.append('"clef-use"={enabled_tools=["computer_capabilities","computer_status"]}')
    return "mcp_servers={" + ",".join(fields) + "}"


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
        config = read_config("codex", (_read(layout["config"]) or b"").decode())
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
            "-c",
            _codex_verification_override(config),
        ]
        argv.append(_verification_prompt(trigger))
        run = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "CLEF_USE_MCP_READ_ONLY": "1"},
        )
        events = []
        for line in run.stdout.splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        trace = layout["state"] / f"verification-{trigger}-trace.jsonl"
        atomic_write(trace, run.stdout)
        result["trace"] = str(trace)
        result["exit_code"] = run.returncode
        loaded = []
        invoked = []
        attempted = []
        failed = False
        any_gui_guide = False
        for event in events:
            item = event.get("item", {})
            selected_tool = (
                item.get("type") == "mcp_tool_call"
                and item.get("server") == "clef-use"
                and item.get("tool") in ("computer_capabilities", "computer_status")
            )
            if selected_tool and event.get("type") in (
                "item.started",
                "item.updated",
                "item.completed",
            ):
                if item["tool"] not in attempted:
                    attempted.append(item["tool"])
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
                    body = (layout["root"] / name / "SKILL.md").read_text()
                    if (
                        _codex_guide_path_in_command(expected[name], item.get("command", ""))
                        and body.strip() in output
                    ):
                        loaded.append(name)
            if selected_tool:
                failed |= (
                    item.get("status") == "failed"
                    or bool(item.get("error"))
                    or _tool_result_failed(item.get("result"))
                )
                if (
                    item.get("status") == "completed"
                    and not item.get("error")
                    and _tool_result_succeeded(item.get("result"))
                ):
                    invoked.append(item["tool"])
        stages.update(_model_stages(loaded, invoked, failed))
        stages["TASK_VERIFIED"]["reason"] = "read-only verification does not execute a GUI fixture"
        selected = (
            "clef-use-blender"
            if trigger == "natural" and "clef-use-blender" in expected
            else "clef-use"
        )
        passed = (
            not any_gui_guide and not attempted
            if trigger == "negative"
            else selected in loaded and bool(invoked)
        )
        outcome = (
            "PASS" if passed and not run.returncode else "NOT_RUN" if run.returncode else "FAIL"
        )
        result.update(status=outcome, model_driven=True)
        result["model_trigger_verification"] = {
            "case": trigger,
            "status": outcome,
            "loaded": loaded,
            "invoked": invoked,
            "attempted": attempted,
            "stages": _model_stages(loaded, invoked, failed),
        }
        if run.returncode:
            result["reason"] = _probe_reason(run.stdout + run.stderr, run.returncode)
    except (OSError, ValueError, queue.Empty, subprocess.TimeoutExpired) as exc:
        result["reason"] = f"actual harness verification failed: {type(exc).__name__}: {exc}"
    return result

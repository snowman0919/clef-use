from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import tomlkit
from ruamel.yaml import YAML


def target_path(harness: str, home: Path | None = None) -> Path:
    home = home or Path.home()
    if harness == "codex":
        return Path(os.environ.get("CODEX_HOME", home / ".codex")) / "config.toml"
    if harness == "hermes":
        return Path(os.environ.get("HERMES_HOME", home / ".hermes")) / "config.yaml"
    if harness == "omp":
        profile = os.environ.get("OMP_PROFILE") or os.environ.get("PI_PROFILE")
        root = Path(os.environ.get("PI_CONFIG_DIR", home / ".omp"))
        if profile:
            if not profile.replace("-", "").replace("_", "").isalnum():
                raise ValueError("unsafe OMP profile")
            return root / "profiles" / profile / "agent/mcp.json"
        return Path(os.environ.get("PI_CODING_AGENT_DIR", root / "agent")) / "mcp.json"
    raise ValueError("harness must be codex, hermes or omp")


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".clef-use-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def install_mcp(
    harness: str, path: Path | None = None, command: str | None = None, dry_run: bool = False
) -> dict:
    path = path or target_path(harness)
    command = command or shutil.which("clef-use") or str(Path(sys.executable).with_name("clef-use"))
    if not Path(command).is_absolute():
        resolved = shutil.which(command)
        if not resolved:
            raise ValueError("MCP executable must be discoverable")
        command = resolved
    entry = {"command": command, "args": ["mcp"]}
    if harness == "codex":
        entry["tool_timeout_sec"] = 3600
    elif harness == "hermes":
        entry["timeout"] = 3600
    else:
        entry.update(type="stdio", timeout=3600000)
    original = path.read_text() if path.exists() else ""
    if harness == "codex":
        data = tomlkit.parse(original)
        servers = data.setdefault("mcp_servers", tomlkit.table())
    elif harness == "hermes":
        yaml = YAML()
        yaml.preserve_quotes = True
        data = yaml.load(original) or {}
        servers = data.setdefault("mcp_servers", {})
    elif harness == "omp":
        data = json.loads(original) if original else {}
        servers = data.setdefault("mcpServers", {})
    else:
        raise ValueError("unknown harness")
    previous = servers.get("clef-use")
    if previous and (
        previous.get("command") != command or list(previous.get("args", [])) != ["mcp"]
    ):
        return {
            "status": "CONFLICT",
            "path": str(path),
            "entry": entry,
            "reason": "existing clef-use entry differs; no configuration was overwritten",
        }
    if harness == "omp" and "clef-use" in data.get("disabledServers", []):
        return {
            "status": "DISABLED",
            "path": str(path),
            "entry": entry,
            "reason": "existing explicit denylist preserved",
        }
    if previous and all(previous.get(k) == v for k, v in entry.items()):
        return {"status": "UNCHANGED", "path": str(path), "entry": entry}
    servers["clef-use"] = {**dict(previous or {}), **entry}
    if harness == "codex":
        output = tomlkit.dumps(data)
    elif harness == "hermes":
        buffer = io.StringIO()
        yaml.dump(data, buffer)
        output = buffer.getvalue()
    else:
        output = json.dumps(data, indent=2) + "\n"
    if not dry_run:
        if path.exists():
            backup = path.with_name(path.name + ".clef-use.bak")
            if not backup.exists():
                atomic_write(backup, original)
        atomic_write(path, output)
    return {"status": "PREVIEW" if dry_run else "INSTALLED", "path": str(path), "entry": entry}

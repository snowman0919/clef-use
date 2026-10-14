from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

import tomlkit
from ruamel.yaml import YAML


def read_config(harness: str, original: str) -> dict:
    if harness == "codex":
        return tomlkit.parse(original)
    if harness == "hermes":
        yaml = YAML()
        yaml.preserve_quotes = True
        return yaml.load(original) or {}
    if harness == "omp":
        return json.loads(original) if original else {}
    raise ValueError("harness must be codex, hermes or omp")


def server_entry(harness: str, original: str) -> dict | None:
    data = read_config(harness, original)
    return (data.get("mcpServers" if harness == "omp" else "mcp_servers") or {}).get("clef-use")


def _json_property(text: str, key: str, replacement: str | None) -> str:
    """Edit one object property without normalizing unrelated JSON bytes."""
    decoder = json.JSONDecoder()
    start = len(text) - len(text.lstrip())
    if text[start] != "{":
        raise ValueError("configuration must be an object")
    position = start + 1
    previous_comma = None
    while True:
        while text[position].isspace():
            position += 1
        if text[position] == "}":
            if replacement is None:
                return text
            prefix = "," if previous_comma is not None else ""
            return text[:position] + prefix + json.dumps(key) + ":" + replacement + text[position:]
        property_start = position
        name, position = decoder.raw_decode(text, position)
        while text[position].isspace():
            position += 1
        if text[position] != ":":
            raise ValueError("invalid object property")
        position += 1
        while text[position].isspace():
            position += 1
        value_start = position
        _, value_end = decoder.raw_decode(text, position)
        position = value_end
        while text[position].isspace():
            position += 1
        if name == key:
            if replacement is not None:
                return text[:value_start] + replacement + text[value_end:]
            if text[position] == ",":
                return text[:property_start] + text[position + 1 :]
            begin = previous_comma if previous_comma is not None else property_start
            return text[:begin] + text[position:]
        if text[position] == ",":
            previous_comma = position
            position += 1
        elif text[position] == "}":
            # Keep the last property's end as the comma insertion marker.
            previous_comma = value_end
        else:
            raise ValueError("invalid object separator")


def render_entry(harness: str, original: str, entry: dict | None) -> str:
    data = read_config(harness, original)
    key = "mcpServers" if harness == "omp" else "mcp_servers"
    if harness == "hermes":
        return _yaml_entry(original, entry)
    if harness == "omp":
        text = original or "{}\n"
        if key not in data:
            return _json_property(text, key, json.dumps({"clef-use": entry})) if entry else text
        # Locate the servers object using the decoder, preserving its surrounding bytes.
        decoder = json.JSONDecoder()
        position = text.index("{") + 1
        while True:
            while text[position].isspace() or text[position] == ",":
                position += 1
            name, position = decoder.raw_decode(text, position)
            position = text.index(":", position) + 1
            while text[position].isspace():
                position += 1
            _, end = decoder.raw_decode(text, position)
            if name == key:
                value = _json_property(
                    text[position:end], "clef-use", json.dumps(entry) if entry else None
                )
                return text[:position] + value + text[end:]
            position = end
    servers = data.setdefault(key, tomlkit.table() if harness == "codex" else {})
    if entry is None:
        servers.pop("clef-use", None)
    else:
        servers["clef-use"] = entry
    if harness == "codex":
        return tomlkit.dumps(data)
    buffer = io.StringIO()
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.dump(data, buffer)
    return buffer.getvalue()


def _yaml_entry(original: str, entry: dict | None) -> str:
    """Splice one YAML server node; preserve every unrelated byte and comment."""
    yaml = YAML()

    def leaf_end(item):
        if getattr(item, "flow_style", False):
            return item.end_mark.index
        if isinstance(item.value, list):
            children = []
            for child in item.value:
                children.extend(child if isinstance(child, tuple) else [child])
            return max((leaf_end(child) for child in children), default=item.end_mark.index)
        return item.end_mark.index

    node = yaml.compose(original)
    pairs = node.value if node is not None else []
    servers = next((value for key, value in pairs if key.value == "mcp_servers"), None)
    newline = "\r\n" if "\r\n" in original else "\n"
    encoded = json.dumps(entry) if entry is not None else None

    def insert_flow(mapping, name, value):
        position = mapping.end_mark.index - 1
        fragment = original[mapping.start_mark.index : mapping.end_mark.index]
        previous = None
        for token in YAML().scan(fragment):
            if token.id == "}" and token.end_mark.index == len(fragment):
                break
            previous = token
        prefix = ", " if mapping.value and previous.id != "," else ""
        return original[:position] + prefix + json.dumps(name) + ": " + value + original[position:]

    if servers is None:
        if entry is None:
            return original
        if node is not None and getattr(node, "flow_style", False):
            return insert_flow(node, "mcp_servers", json.dumps({"clef-use": entry}))
        position = node.end_mark.index if node is not None else len(original)
        separator = "" if not position or original[position - 1] in ("\n", "\r") else newline
        addition = separator + "mcp_servers:" + newline + "  clef-use: " + encoded + newline
        return original[:position] + addition + original[position:]
    if not isinstance(servers.value, list):
        if servers.value == "":
            return (
                original[: servers.start_mark.index]
                + ("{}" if entry is None else json.dumps({"clef-use": entry}))
                + original[servers.end_mark.index :]
            )
        raise ValueError("mcp_servers must be a mapping")
    selected = next(
        (
            (index, key, value)
            for index, (key, value) in enumerate(servers.value)
            if key.value == "clef-use"
        ),
        None,
    )
    if selected is None:
        if entry is None:
            return original
        if servers.flow_style:
            return insert_flow(servers, "clef-use", encoded)
        indent = servers.value[0][0].start_mark.column if servers.value else 2
        position = servers.end_mark.index - servers.end_mark.column
        addition = " " * indent + "clef-use: " + encoded + newline
        if position and original[position - 1] not in ("\n", "\r"):
            addition = newline + addition
        return original[:position] + addition + original[position:]
    index, key, value = selected
    if entry is not None:
        end = value.end_mark.index if value.flow_style else leaf_end(value)
        return original[: value.start_mark.index] + encoded + original[end:]
    if servers.flow_style:
        start, end = key.start_mark.index, value.end_mark.index
        if index + 1 < len(servers.value):
            end = servers.value[index + 1][0].start_mark.index
        elif index:
            start = original.rfind(",", servers.value[index - 1][1].end_mark.index, start)
        return original[:start] + original[end:]

    # Mapping end marks include following indentation/comments; stop at the final leaf.
    start = key.start_mark.index - key.start_mark.column
    end = leaf_end(value)
    # Remove the rest of this owned entry's last line, leaving following comments intact.
    end = original.find("\n", end)
    end = len(original) if end == -1 else end + 1
    if len(servers.value) == 1:
        # Preserve a valid empty mapping so a later reinstall can add an entry.
        return original[: servers.start_mark.index] + "{}" + newline + original[end:]
    return original[:start] + original[end:]


def omp_profile() -> str | None:
    # Native OMP treats an explicitly empty canonical variable as default.
    selected = os.environ.get("OMP_PROFILE", os.environ.get("PI_PROFILE", "")).strip()
    if selected in ("", "default"):
        return None
    if (
        not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", selected)
        or selected.endswith(".")
        or re.match(r"^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)", selected, re.I)
    ):
        raise ValueError("unsafe OMP profile")
    return selected


def target_path(harness: str, home: Path | None = None) -> Path:
    home = home or Path.home()
    if harness == "codex":
        return Path(os.environ.get("CODEX_HOME", home / ".codex")) / "config.toml"
    if harness == "hermes":
        return Path(os.environ.get("HERMES_HOME", home / ".hermes")) / "config.yaml"
    if harness == "omp":
        profile = omp_profile()
        name = Path(os.environ.get("PI_CONFIG_DIR") or ".omp")
        if name.is_absolute():
            raise ValueError(
                "PI_CONFIG_DIR must be a name relative to HOME; "
                "use PI_CODING_AGENT_DIR for an absolute default agent directory"
            )
        root = home / name
        if profile:
            return root / "profiles" / profile / "agent/mcp.json"
        return Path(os.environ.get("PI_CODING_AGENT_DIR") or root / "agent").absolute() / "mcp.json"
    raise ValueError("harness must be codex, hermes or omp")


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=".clef-use-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def install_mcp(
    harness: str,
    path: Path | None = None,
    command: str | None = None,
    dry_run: bool = False,
    *,
    managed_entry: dict | None = None,
) -> dict:
    path = path or target_path(harness)
    launcher_name = "clef-use.exe" if sys.platform == "win32" else "clef-use"
    local_launcher = Path(sys.executable).with_name(launcher_name)
    local_available = local_launcher.is_file() and (
        sys.platform == "win32" or os.access(local_launcher, os.X_OK)
    )
    command = command or (
        str(local_launcher)
        if local_available
        else shutil.which(launcher_name) or str(local_launcher)
    )
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
    original = path.read_bytes().decode("utf-8") if path.exists() else ""
    data = read_config(harness, original)
    previous = server_entry(harness, original)
    if previous and (previous.get("enabled") is False or previous.get("disabled") is True):
        return {
            "status": "DISABLED",
            "path": str(path),
            "entry": entry,
            "reason": "existing explicit disabled setting preserved",
        }
    if (
        previous
        and previous != managed_entry
        and (previous.get("command") != command or list(previous.get("args", [])) != ["mcp"])
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
    output = render_entry(harness, original, {**dict(previous or {}), **entry})
    if not dry_run:
        if path.exists():
            backup = path.with_name(path.name + ".clef-use.bak")
            if not backup.exists():
                atomic_write(backup, original)
        atomic_write(path, output)
    return {"status": "PREVIEW" if dry_run else "INSTALLED", "path": str(path), "entry": entry}

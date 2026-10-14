import json
import os
import shutil
import subprocess
import sys

import pytest

from clef_use.integrations import _codex_guide_path_in_command, _codex_verification_profile


@pytest.mark.parametrize("separator", ["\\", "\\\\", "/"])
def test_codex_windows_guide_command_preserves_native_path_identity(separator):
    path = r"C:\Users\profile space\.agents\skills\clef-use\SKILL.md"
    represented = path.replace("\\", separator)
    command = f'"pwsh.exe" -Command "Get-Content -Raw -LiteralPath \'{represented}\'"'
    assert _codex_guide_path_in_command(path, command)
    assert not _codex_guide_path_in_command(path, command.replace("clef-use", "other-guide"))
    for suffix in (".bak", "~", "+backup", ":copy"):
        assert not _codex_guide_path_in_command(
            path, command.replace("SKILL.md", "SKILL.md" + suffix)
        )


@pytest.mark.parametrize("global_selected", [False, True])
@pytest.mark.parametrize("trusted_project", [False, True])
def test_native_codex_project_profile_binds_approved_transport_and_reader_scope(
    tmp_path, monkeypatch, global_selected, trusted_project
):
    executable = shutil.which("codex")
    if not executable:
        pytest.skip("native Codex CLI is unavailable")
    import tomlkit

    home = tmp_path / "codex-home"
    home.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(home))
    project = tmp_path / "untrusted-project"
    (project / ".codex").mkdir(parents=True)
    names = ["node_repl", "avatarforge-host", "server.with.dot", 'server "quote"', "ローカル"]
    data = {"mcp_servers": {name: {"command": sys.executable, "args": []} for name in names}}
    data["mcp_servers"]["remote"] = {"url": "https://example.invalid/mcp"}
    if trusted_project:
        data["projects"] = {str(project): {"trust_level": "trusted"}}
    if global_selected:
        data["mcp_servers"]["clef-use"] = {
            "command": sys.executable,
            "args": ["-V"],
            "enabled": False,
        }
    entry = {
        "command": sys.executable,
        "args": ["-m", "clef_use.cli", "mcp"],
        "env": {"CLEF_USE_CONFIG": "owned-config.toml", "SERVER_VALUE": "private-sentinel"},
        "tool_timeout_sec": 60,
    }
    local = project / ".codex/config.toml"
    local_servers = {"clef-use": {**entry, "env": {"CLEF_USE_MCP_READ_ONLY": "0"}}}
    if trusted_project:
        local_servers["project-server"] = {
            "command": sys.executable,
            "args": ["-V"],
            "enabled": True,
        }
    local.write_text(tomlkit.dumps({"mcp_servers": local_servers}), encoding="utf-8")
    local_before = local.read_bytes()
    config = home / "config.toml"
    config.write_text(tomlkit.dumps(data), encoding="utf-8")
    before = config.read_bytes()
    with _codex_verification_profile(executable, project, entry) as config_args:
        private_config = home / (config_args[1] + ".config.toml")
        assert "private-sentinel" not in " ".join(config_args)
        if os.name != "nt":
            assert private_config.stat().st_mode & 0o777 == 0o600
        result = subprocess.run(
            [executable, *config_args, "-C", str(project), "mcp", "list", "--json"],
            stdin=subprocess.DEVNULL,
            cwd=project,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        servers = {item["name"]: item for item in json.loads(result.stdout)}
        assert {name for name, server in servers.items() if server["enabled"]} == {"clef-use"}
        selected = servers["clef-use"]["transport"]
        assert selected["command"] == entry["command"]
        assert selected["args"] == entry["args"]
        assert selected["env"] == {**entry["env"], "CLEF_USE_MCP_READ_ONLY": "1"}
    assert not private_config.exists()
    assert config.read_bytes() == before
    assert local.read_bytes() == local_before


def test_native_codex_profile_preserves_user_edits_and_cleans_unchanged_on_failure(
    tmp_path, monkeypatch
):
    executable = shutil.which("codex")
    if not executable:
        pytest.skip("native Codex CLI is unavailable")
    home = tmp_path / "codex-home"
    home.mkdir()
    monkeypatch.setenv("CODEX_HOME", str(home))
    (home / "config.toml").write_text("")
    entry = {"command": sys.executable, "args": ["-m", "clef_use.cli", "mcp"]}
    with pytest.raises(RuntimeError, match="consumer interrupted"):
        with _codex_verification_profile(executable, tmp_path, entry) as config_args:
            path = home / (config_args[1] + ".config.toml")
            raise RuntimeError("consumer interrupted")
    assert not path.exists()
    with pytest.raises(ValueError, match="modified temporary Codex profile preserved"):
        with _codex_verification_profile(executable, tmp_path, entry) as config_args:
            path = home / (config_args[1] + ".config.toml")
            changed = path.read_bytes() + b"\n# User edit\n"
            path.write_bytes(changed)
    assert path.read_bytes() == changed

import json
import os
import shutil
import subprocess
import sys

import pytest

from clef_use.harness import render_entry
from clef_use.integrations import _codex_verification_override


def test_native_codex_read_only_overrides_preserve_named_transports(tmp_path):
    executable = shutil.which("codex")
    if not executable:
        pytest.skip("native Codex CLI is unavailable")
    import tomlkit

    home = tmp_path / "codex-home"
    home.mkdir()
    names = ["node_repl", "avatarforge-host", "server.with.dot", 'server "quote"', "ローカル"]
    data = {"mcp_servers": {name: {"command": sys.executable, "args": []} for name in names}}
    text = render_entry("codex", tomlkit.dumps(data), {"command": sys.executable, "args": ["-V"]})
    config = home / "config.toml"
    config.write_text(text, encoding="utf-8")
    before = config.read_bytes()
    result = subprocess.run(
        [
            executable,
            "-c",
            _codex_verification_override(data),
            "mcp",
            "list",
            "--json",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env={**os.environ, "CODEX_HOME": str(home)},
        timeout=30,
        check=True,
    )
    servers = {item["name"]: item for item in json.loads(result.stdout)}
    for name in names:
        assert servers[name]["enabled"] is False
        assert servers[name]["transport"]["command"] == sys.executable
    assert servers["clef-use"]["enabled"] is True
    assert servers["clef-use"]["transport"]["args"] == ["-V"]
    assert config.read_bytes() == before

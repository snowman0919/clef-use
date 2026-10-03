"""Probe an upstream Hermes MCP client against the canonical fixture service."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import tempfile
import threading
from pathlib import Path

import yaml

from clef_use.benchmark import fixture_runtime
from clef_use.service import SessionManager, make_server


def check(source: Path, source_revision: str, launcher: Path) -> dict:
    if not (source / "tools/mcp_tool.py").is_file() or not launcher.is_file():
        raise ValueError("upstream Hermes source and installed launcher are required")
    config = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "config.yaml"
    original = config.read_bytes()
    entry = yaml.safe_load(original)["mcp_servers"]["clef-use"]
    if entry.get("command") != str(launcher) or entry.get("args") != ["mcp"]:
        raise ValueError("installed Hermes entry differs from the requested launcher")
    with tempfile.TemporaryDirectory(prefix="clef-use-hermes-probe-") as temporary:
        root = Path(temporary)
        token = secrets.token_urlsafe(32)
        manager = SessionManager(fixture_runtime)
        server = make_server(manager, token)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        endpoint = root / "endpoint.json"
        endpoint.write_text(
            json.dumps({"port": server.server_port, "token": token, "pid": os.getpid()})
        )
        endpoint.chmod(0o600)
        home = root / "hermes"
        home.mkdir(mode=0o700)
        # Hermes deliberately filters inherited environment; scope the fixture explicitly.
        entry = {
            **entry,
            "env": {
                "CLEF_USE_STATE_DIR": str(root),
                "CLEF_USE_CONFIG": str(root / "absent.toml"),
            },
        }
        (home / "config.yaml").write_text(yaml.safe_dump({"mcp_servers": {"clef-use": entry}}))
        os.environ["HERMES_HOME"] = str(home)
        sys.path.insert(0, str(source))
        from tools.mcp_tool_discovery import register_mcp_servers
        from tools.mcp_tool_lifecycle import shutdown_mcp_servers
        from tools.mcp_tool_schema import mcp_prefixed_tool_name
        from tools.registry import registry

        try:
            names = register_mcp_servers({"clef-use": entry})
            expected = {
                mcp_prefixed_tool_name("clef-use", name)
                for name in (
                    "computer_run",
                    "computer_continue",
                    "computer_observe",
                    "computer_status",
                    "computer_abort",
                )
            }
            if not expected.issubset(names):
                raise RuntimeError(f"Hermes registered tools: {names}; expected {sorted(expected)}")
            tool = registry.get_entry(mcp_prefixed_tool_name("clef-use", "computer_run"))
            envelope = json.loads(
                tool.handler({"goal": "Open Settings and apply size 16", "max_steps": 8})
            )
            result = envelope.get("structuredContent", envelope["result"])
            if isinstance(result, str):
                result = json.loads(result)
            assert result["status"] == "COMPLETED" and result["steps"] == 2
            assert manager.get(result["session_id"]).rounds == 4
            assert config.read_bytes() == original
            return {
                "source": "NousResearch/hermes-agent",
                "revision": source_revision,
                "transport": "official native MCP discovery and registry handler",
                "installed_runtime_version": __import__("clef_use").__version__,
                "tools": sorted(expected),
                "harness_generated_utility_tools": sorted(set(names) - expected),
                "status": result["status"],
                "actions": result["steps"],
                "decisions": result["rounds"],
                "native_input": False,
                "outer_llm_interventions": 0,
                "configuration_preserved": True,
                "boundary": "fixture service; existing full Hermes launcher remains unavailable",
            }
        finally:
            shutdown_mcp_servers()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--launcher", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.source, args.source_revision, args.launcher)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

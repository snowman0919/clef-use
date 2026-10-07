"""Probe an upstream Hermes MCP client against the canonical fixture service."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import yaml

from clef_use.benchmark import fixture_runtime
from clef_use.service import SessionManager, make_server

HANDLER_PROBE = r"""
import json
import inspect
from hermes_cli.config import load_config
from tools.mcp_tool_discovery import register_mcp_servers
from tools.mcp_tool_lifecycle import shutdown_mcp_servers
from tools.mcp_tool_schema import mcp_prefixed_tool_name
from tools.registry import registry

try:
    names = register_mcp_servers(load_config()["mcp_servers"])
    expected = {mcp_prefixed_tool_name("clef-use", name) for name in (
        "computer_run", "computer_continue", "computer_observe",
        "computer_status", "computer_abort")}
    assert expected.issubset(names)
    tool = registry.get_entry(mcp_prefixed_tool_name("clef-use", "computer_run"))
    envelope = json.loads(tool.handler({"goal": "Open Settings and apply size 16", "max_steps": 8}))
    result = envelope.get("structuredContent", envelope.get("result"))
    if isinstance(result, str):
        result = json.loads(result)
    assert result["status"] == "COMPLETED" and result["steps"] == 2 and result["rounds"] == 4
    print("CLEF_PROBE:" + json.dumps({"tools": sorted(expected),
        "harness_generated_utility_tools": sorted(set(names) - expected),
        "status": result["status"], "actions": result["steps"], "decisions": result["rounds"],
        "client_source": inspect.getfile(load_config),
        "discovery_source": inspect.getfile(register_mcp_servers)}))
finally:
    shutdown_mcp_servers()
"""


def check_processes(source, source_revision, launcher, hermes_cli, hermes_python):
    """Exercise the full upstream CLI and its handler in separate interpreter processes."""
    for executable in (launcher, hermes_cli, hermes_python):
        if not executable.is_file():
            raise ValueError("all three installed executables are required")
    with tempfile.TemporaryDirectory(prefix="clef-use-hermes-process-") as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        manager = SessionManager(fixture_runtime)
        token = secrets.token_urlsafe(32)
        server = make_server(manager, token)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        endpoint = root / "endpoint.json"
        endpoint.write_text(
            json.dumps({"port": server.server_port, "token": token, "pid": os.getpid()})
        )
        endpoint.chmod(0o600)
        home = root / "hermes"
        home.mkdir(mode=0o700)
        config = home / "config.yaml"
        config.write_text(
            yaml.safe_dump(
                {
                    "mcp_servers": {
                        "clef-use": {
                            "command": str(launcher.resolve()),
                            "args": ["mcp"],
                            "env": {
                                "CLEF_USE_STATE_DIR": str(root),
                                "CLEF_USE_CONFIG": str(root / "absent.toml"),
                            },
                        }
                    }
                }
            )
        )
        original = config.read_bytes()
        environment = {**os.environ, "HERMES_HOME": str(home)}
        environment.pop("PYTHONPATH", None)
        thread.start()
        try:
            cli = subprocess.run(
                [str(hermes_cli), "mcp", "test", "clef-use"],
                env=environment,
                capture_output=True,
                text=True,
                timeout=90,
            )
            if cli.returncode:
                raise RuntimeError(f"Hermes CLI connection exited {cli.returncode}")
            handler = subprocess.run(
                [str(hermes_python), "-c", HANDLER_PROBE],
                env=environment,
                capture_output=True,
                text=True,
                timeout=90,
            )
            if handler.returncode:
                raise RuntimeError(f"Hermes native handler exited {handler.returncode}")
            lines = [line for line in handler.stdout.splitlines() if line.startswith("CLEF_PROBE:")]
            if len(lines) != 1:
                raise RuntimeError("Hermes handler did not produce one result")
            result = json.loads(lines[0].removeprefix("CLEF_PROBE:"))
            for key in ("client_source", "discovery_source"):
                if not Path(result.pop(key)).resolve().is_relative_to(source.resolve()):
                    raise RuntimeError("Hermes loaded a different upstream source tree")
            sessions = list(manager.sessions.values())
            assert len(sessions) == 1 and sessions[0].steps == 2 and sessions[0].rounds == 4
            assert config.read_bytes() == original
            return {
                "source": "NousResearch/hermes-agent",
                "revision": source_revision,
                "transport": (
                    "official CLI mcp test and native registry handler, separate processes"
                ),
                "cli_exit": cli.returncode,
                "handler_exit": handler.returncode,
                "installed_runtime_version": __import__("clef_use").__version__,
                **result,
                "configuration_preserved": True,
                "client_source_tree_verified": True,
                "native_input": False,
                "outer_llm_interventions": 0,
                "boundary": (
                    "isolated fixture service; existing user launcher/settings unchanged; "
                    "no agent LLM conversation"
                ),
            }
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


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
    parser.add_argument("--hermes-cli", type=Path)
    parser.add_argument("--hermes-python", type=Path)
    args = parser.parse_args()
    if bool(args.hermes_cli) != bool(args.hermes_python):
        parser.error("--hermes-cli and --hermes-python must be supplied together")
    result = (
        check_processes(
            args.source, args.source_revision, args.launcher, args.hermes_cli, args.hermes_python
        )
        if args.hermes_cli
        else check(args.source, args.source_revision, args.launcher)
    )
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

"""Actual native Codex/MCP task on a disposable Windows Continue/Confirm GUI.

Run in the user's InteractiveToken session with the installed runtime Python.
The controller reads only /result and /finish from the diagnostic GUI endpoint;
all task input belongs to the unmodified installed MCP/runtime. Native approval
requests outside the preauthorized GUI run and its fresh observation stop the
attempt. Policy and sandbox are inherited; each matching request is accepted once.
Private redacted protocol messages, stderr and screenshots stay beside output.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import queue
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from clef_use import __version__, integrations
from clef_use.capabilities import digest, tool_schemas
from clef_use.client import RuntimeClient
from clef_use.harness import read_config, server_entry
from clef_use.windows_input import Point, WindowsInput

TOOLS = {
    "computer_capabilities",
    "computer_run",
    "computer_continue",
    "computer_observe",
    "computer_status",
    "computer_abort",
}
GOAL = "Make Task complete visible using Continue then Confirm."
CONDITIONS = ["Task complete is visible"]

# Transparent private request/reply archive, matching the existing Blender
# benchmark's worker instrumentation. No installed file or model value changes.
REQUEST_ARCHIVE = r"""
import os, sys
if not sys.argv[0].endswith("model_worker.py"):
    import hashlib, json, time, uuid
    from pathlib import Path
    from clef_use.backends import DesktopCapture, JsonWorker
    root = Path(os.environ["CLEF_USE_PRIVATE_REQUEST_ARCHIVE"])
    (root / ("hook-" + str(os.getpid()) + ".json")).write_text(json.dumps({
        "pid":os.getpid(), "loaded":True,
    }))
    original_capture = DesktopCapture.capture
    def archived_capture(self):
        frame = original_capture(self)
        prefix = "capture-" + str(os.getpid()) + "-" + uuid.uuid4().hex
        frame.image.save(root / (prefix + ".png"))
        (root / (prefix + ".json")).write_text(json.dumps({
            "reference":frame.reference().model_dump(mode="json"),
            "returned_at_ns":time.monotonic_ns(),
        }))
        return frame
    DesktopCapture.capture = archived_capture
    original = JsonWorker.request
    def archived_request(self, payload):
        prefix = self.kind + "-" + str(os.getpid()) + "-" + uuid.uuid4().hex
        encode = lambda value: json.dumps(value, ensure_ascii=False).encode("utf-8")
        raw = encode(payload)
        (root / (prefix + "-request.json")).write_bytes(raw)
        stamp = {"requested_at_ns":time.monotonic_ns()}
        (root / (prefix + "-time.json")).write_text(json.dumps(stamp))
        result = original(self, payload)
        if encode(payload) != raw:
            raise RuntimeError("Private archive observed mutation of the submitted worker request")
        (root / (prefix + "-reply.json")).write_bytes(encode(result))
        (root / (prefix + "-identity.json")).write_text(json.dumps({
            "input_sha256_before_after":hashlib.sha256(raw).hexdigest(),
            "worker_kind":self.kind, "replied_at_ns":time.monotonic_ns(),
        }))
        return result
    JsonWorker.request = archived_request
"""


def redact(value):
    if isinstance(value, dict):
        return {
            key: "[redacted]"
            if key.lower()
            in {
                "token",
                "access_token",
                "refresh_token",
                "id_token",
                "authorization",
                "api_key",
                "apikey",
                "password",
                "credential",
            }
            else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"(?:Bearer\s+|sk-)[A-Za-z0-9_.-]+", "[redacted]", value)
    return value


class NativeRequestBlocked(RuntimeError):
    pass


class AppServer:
    """Native line-delimited JSON-RPC, with no emulated tool responses."""

    def __init__(self, executable, cwd, environment, root, configuration_overrides):
        self.trace = root / "codex-private-trace.jsonl"
        self.stderr = root / "codex-private-stderr.txt"
        self.messages = queue.Queue()
        self.events = []
        self.blocked_requests = []
        self.approved_requests = []
        self.approve_request = None
        self.serial = 0
        self.stream = self.trace.open("x", encoding="utf-8", buffering=1)
        self.error_stream = self.stderr.open("x", encoding="utf-8", buffering=1)
        argv = [executable]
        for override in configuration_overrides:
            argv.extend(("--config", override))
        self.process = subprocess.Popen(
            [*argv, "app-server", "--stdio"],
            cwd=cwd,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        def stdout():
            for line in self.process.stdout:
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    self.error_stream.write(str(redact(line)))
                    continue
                self.stream.write(json.dumps(redact(message)) + "\n")
                self.messages.put(message)
            self.messages.put(None)

        def stderr():
            for line in self.process.stderr:
                self.error_stream.write(str(redact(line)))

        self.readers = [threading.Thread(target=f, daemon=True) for f in (stdout, stderr)]
        for reader in self.readers:
            reader.start()

    def send(self, message):
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()

    def next(self, timeout, stop_on_request=True):
        message = self.messages.get(timeout=max(0.001, timeout))
        if message is None:
            raise RuntimeError("Native Codex app-server exited before the expected result")
        if "method" in message:
            self.events.append(message)
            if "id" in message:
                if self.approve_request is not None and self.approve_request(message):
                    self.approved_requests.append(
                        {
                            "method": message["method"],
                            "tool": message["params"]["message"].split('"')[1],
                            "request_sha256": digest(redact(message)),
                            "scope": "One preauthorized owned GUI request; no persistence",
                        }
                    )
                    self.send(
                        {
                            "id": message["id"],
                            "result": {
                                "action": "accept",
                                "content": {},
                                "_meta": None,
                            },
                        }
                    )
                    return message
                self.blocked_requests.append(
                    {
                        "method": message["method"],
                        "request_id": message["id"],
                        "parameter_fields": sorted(message.get("params", {})),
                        "redacted_request_sha256": digest(redact(message)),
                        "private_trace_retained": True,
                    }
                )
                if message["method"] == "mcpServer/elicitation/request":
                    self.send(
                        {
                            "id": message["id"],
                            "result": {
                                "action": "decline",
                                "content": None,
                                "_meta": None,
                            },
                        }
                    )
                else:
                    self.send(
                        {
                            "id": message["id"],
                            "error": {
                                "code": -32601,
                                "message": (
                                    "Native request retained; this controller cannot approve it"
                                ),
                            },
                        }
                    )
                if stop_on_request:
                    raise NativeRequestBlocked(
                        "Native request requires interaction: " + message["method"]
                    )
        return message

    def rpc(self, method, params, timeout=30, stop_on_request=True):
        self.serial += 1
        identifier = self.serial
        self.send({"id": identifier, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self.next(deadline - time.monotonic(), stop_on_request)
            if message.get("id") == identifier:
                if "error" in message:
                    error = message["error"]
                    raise RuntimeError(
                        f"Native {method} RPC error {error.get('code')}: "
                        + str(redact(error.get("message", "")))
                    )
                return message["result"]
        raise TimeoutError("Native RPC deadline: " + method)

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        for reader in self.readers:
            reader.join(timeout=2)
        self.stream.close()
        self.error_stream.close()


def tool_payload(item):
    result = item.get("result")
    if item.get("status") != "completed" or item.get("error"):
        return None
    if not integrations._tool_result_succeeded(result):
        return None
    if isinstance(result.get("structuredContent"), dict):
        return result["structuredContent"]
    for content in result.get("content", []):
        if isinstance(content, dict) and content.get("type") == "text":
            try:
                value = json.loads(content.get("text", ""))
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(value, dict):
                return value
    return None


def completed_items(events):
    return [
        event.get("params", {}).get("item", {})
        for event in events
        if event.get("method") == "item/completed"
    ]


def task_evidence(events, guides, schema_hash):
    loaded, calls = [], []
    capabilities_verified = False
    for item in completed_items(events):
        if item.get("type") == "commandExecution" and item.get("exitCode") == 0:
            output = item.get("aggregatedOutput", "").replace("\r\n", "\n")
            for name, body in guides.items():
                if body.strip() in output and name not in loaded:
                    loaded.append(name)
        if item.get("type") == "mcpToolCall" and item.get("server") == "clef-use":
            payload = tool_payload(item)
            calls.append(
                {
                    "tool": item.get("tool"),
                    "arguments": item.get("arguments", {}),
                    "payload": payload,
                    "core_loaded_before": "clef-use" in loaded,
                    "capabilities_verified_before": capabilities_verified,
                    "native_status": item.get("status"),
                    "native_error": bool(item.get("error")),
                }
            )
            if item.get("tool") == "computer_capabilities" and payload:
                capabilities_verified |= (
                    payload.get("schema_sha256") == schema_hash
                    and payload.get("runtime_version") == __version__
                )
    attempts = {}
    for event in events:
        item = event.get("params", {}).get("item", {})
        if (
            event.get("method") in ("item/started", "item/completed")
            and item.get("type") == "mcpToolCall"
            and item.get("server") == "clef-use"
        ):
            attempts[item.get("id", "missing-" + str(len(attempts)))] = item.get("tool")
    runs = [call for call in calls if call["tool"] == "computer_run"]
    run = runs[0] if len(runs) == 1 else None
    result = run["payload"] if run else None
    session_id = result.get("session_id") if result else None
    fresh = False
    if run:
        fresh = any(
            call["tool"] == "computer_observe"
            and call["payload"]
            and call["arguments"].get("session_id") == session_id
            and call["arguments"].get("refresh", True) is True
            for call in calls[calls.index(run) + 1 :]
        )
    bounded = bool(
        run
        and list(attempts.values()).count("computer_run") == 1
        and "computer_continue" not in attempts.values()
        and run["core_loaded_before"]
        and run["capabilities_verified_before"]
        and run["arguments"].get("goal") == GOAL
        and run["arguments"].get("success_conditions") == CONDITIONS
        and run["arguments"].get("max_steps") == 8
        and run["arguments"].get("confidence_threshold") == 0.9
        and run["arguments"].get("execution_mode", "AUTO") == "AUTO"
        and not any(
            run["arguments"].get(name)
            for name in (
                "operation",
                "visual_intent",
                "text_inputs",
                "pointer_inputs",
                "constraints",
            )
        )
    )
    return {
        "loaded": loaded,
        "calls": calls,
        "attempts": list(attempts.values()),
        "run": result,
        "bounded_run": bounded,
        "fresh_observe_after_run": fresh,
    }


def main(args):
    if sys.platform != "win32":
        raise RuntimeError("Requires an actual interactive Windows owner session")
    if not 60 <= args.timeout <= 1000:
        raise ValueError("Native turn deadline must be between60and1000seconds")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump({"status": "STARTING"}, stream)
    root = args.output.parent
    workspace, fixture, state = [
        root / name for name in ("codex-workspace", "gui", "runtime-state")
    ]
    for directory in (workspace, fixture, state):
        directory.mkdir(mode=0o700, exist_ok=False)
    report = {
        "status": "FAILED",
        "classification": "ACTUAL_NATIVE_WINDOWS_CODEX_MCP_GUI",
        "runtime_version": __version__,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "approval_policy_overridden": False,
        "sandbox_overridden": False,
        "model_overridden": False,
        "uses_action_bridge": False,
        "model_turns_started": 0,
    }
    native, point = WindowsInput(), Point()
    app = gui = thread_id = turn_id = None
    gui_streams = []
    old_state = os.environ.get("CLEF_USE_STATE_DIR")
    config_path = None
    original_config = None
    observer_stop = threading.Event()
    observer = None

    def save():
        args.output.write_text(json.dumps(redact(report), indent=2) + "\n", encoding="utf-8")

    def endpoint(operation):
        if operation not in ("result", "finish"):
            raise RuntimeError("Controller diagnostic route is not permitted")
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/{operation}",
            data=b"{}",
            method="POST",
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            diagnostic = json.loads(exc.read())
            raise RuntimeError("Owned diagnostic route failed: " + json.dumps(diagnostic)) from exc

    try:
        report["desktop"] = native.desktop_status()
        previous = native.foreground()
        with native.physical_coordinates():
            if not native.user.GetCursorPos(ctypes.byref(point)) or not previous:
                raise RuntimeError("Original pointer/foreground restoration target unavailable")
        previous_pointer = (point.x, point.y)
        native.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
        native.user.GetAsyncKeyState.restype = ctypes.c_short
        if any(native.user.GetAsyncKeyState(vk) & 0x8000 for vk in range(1, 256)):
            raise RuntimeError("External input is held; GUI attempt refused")
        layout = integrations._layout("codex")
        config_path = layout["config"]
        original_config = config_path.read_bytes()
        config = read_config("codex", original_config.decode("utf-8"))
        entry = server_entry("codex", original_config.decode("utf-8"))
        verification = integrations.verify("codex", live=False)
        if (
            not entry
            or verification["stages"]["INSTALLED"]["status"] != "PASS"
            or verification.get("compatibility", {}).get("status") != "MATCH"
        ):
            raise RuntimeError(
                "Managed installed Codex integration is not compatible and unchanged"
            )
        manifest = integrations._load_manifest(layout)
        guides = {
            name: (layout["root"] / name / "SKILL.md").read_text(encoding="utf-8")
            for name in manifest["skills"]
        }
        if "clef-use" not in guides:
            raise RuntimeError("Managed core guide is not installed")
        report["guide_sha256"] = {
            name: hashlib.sha256((layout["root"] / name / "SKILL.md").read_bytes()).hexdigest()
            for name in guides
        }
        report["configured_fields"] = {
            name: config.get(name, "UNSET")
            for name in ("model", "model_provider", "approval_policy", "sandbox_mode")
        }
        report["managed_command_sha256"] = digest(entry["command"])
        report["managed_arguments_sha256"] = digest(entry.get("args", []))
        expected_schemas = tool_schemas()
        if set(expected_schemas) != TOOLS:
            raise RuntimeError("Installed full MCP tool set changed; inspect actual schemas")
        codex = shutil.which("codex")
        if not codex:
            raise RuntimeError("Native Codex executable is unavailable")
        environment = dict(os.environ, CLEF_USE_STATE_DIR=str(state), PYTHONUTF8="1")
        archive, hook = root / "private-worker-packets", root / "private-instrumentation"
        archive.mkdir(mode=0o700, exist_ok=False)
        hook.mkdir(mode=0o700, exist_ok=False)
        (hook / "sitecustomize.py").write_text(REQUEST_ARCHIVE, encoding="ascii")
        environment["CLEF_USE_PRIVATE_REQUEST_ARCHIVE"] = str(archive)
        environment["PYTHONPATH"] = str(hook) + (
            os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else ""
        )
        report["private_worker_archive"] = {
            "enabled": True,
            "installed_files_modified": False,
            "scope": "Transparent worker request/reply archive; not a timing comparison",
        }
        if (
            environment.get("CLEF_USE_MCP_READ_ONLY") == "1"
            or entry.get("env", {}).get("CLEF_USE_MCP_READ_ONLY") == "1"
        ):
            raise RuntimeError("Existing read-only MCP environment does not admit this GUI task")
        os.environ["CLEF_USE_STATE_DIR"] = str(state)
        token = secrets.token_hex(32)
        (fixture / "gui-token").write_text(token, encoding="utf-8")
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        for name in ("stdout", "stderr"):
            gui_streams.append(
                (root / ("gui-private-" + name + ".txt")).open("x", encoding="utf-8")
            )
        gui = subprocess.Popen(
            [
                sys.executable,
                str(args.fixture_script),
                "--root",
                str(fixture),
                "--port",
                str(port),
                "--canonical-layout",
            ],
            env=environment,
            stdout=gui_streams[0],
            stderr=gui_streams[1],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        deadline = time.monotonic() + 20
        while not (fixture / "windows-model-agent-ready.json").exists():
            if gui.poll() is not None:
                raise RuntimeError("Owned GUI exited before readiness; private stderr retained")
            if time.monotonic() >= deadline:
                raise TimeoutError("Owned GUI readiness deadline")
            time.sleep(0.05)
        receiver = json.loads((fixture / "windows-model-agent-ready.json").read_text())

        def observe_foreground():
            previous_window = None
            with (root / "foreground-private-observations.jsonl").open(
                "x", encoding="utf-8", buffering=1
            ) as stream:
                while not observer_stop.is_set():
                    current = native.foreground()
                    if current != previous_window:
                        pid = ctypes.c_uint32()
                        native.user.GetWindowThreadProcessId(current, ctypes.byref(pid))
                        stream.write(
                            json.dumps(
                                {
                                    "observed_at_ns": time.monotonic_ns(),
                                    "window": current,
                                    "pid": pid.value,
                                    "owned_gui": current == receiver["foreground_window"],
                                }
                            )
                            + "\n"
                        )
                        previous_window = current
                    observer_stop.wait(0.05)

        observer = threading.Thread(target=observe_foreground, daemon=True)
        observer.start()
        # App-server initializes MCP before thread/start overrides are applied.
        # Restrict this child at startup, using the canonical adapter's quoting.
        server_override = integrations._codex_verification_override(config)
        readonly = 'enabled_tools=["computer_capabilities","computer_status"]'
        if server_override.count(readonly) != 1:
            raise RuntimeError("Canonical Codex verification override changed")
        private_environment = {
            key: environment[key]
            for key in ("CLEF_USE_STATE_DIR", "PYTHONPATH", "CLEF_USE_PRIVATE_REQUEST_ARCHIVE")
        }
        env_toml = ",".join(
            json.dumps(key) + "=" + json.dumps(value) for key, value in private_environment.items()
        )
        server_override = server_override.replace(
            readonly,
            "enabled_tools="
            + json.dumps(sorted(TOOLS), separators=(",", ":"))
            + ",env={"
            + env_toml
            + "}",
        )
        plugins = {name: set() for name in config.get("plugins", {})}
        cache = config_path.parent / "plugins/cache"
        if cache.exists():
            for market in cache.iterdir():
                if not market.is_dir():
                    continue
                for package in market.iterdir():
                    if not package.is_dir():
                        continue
                    servers = plugins.setdefault(package.name + "@" + market.name, set())
                    for metadata in package.glob("*/.mcp.json"):
                        document = json.loads(metadata.read_text(encoding="utf-8-sig"))
                        entries = document.get("mcpServers", {})
                        if not isinstance(entries, dict):
                            raise RuntimeError("Installed plugin MCP metadata is not a mapping")
                        servers.update(entries)
        fields = []
        for name, servers in plugins.items():
            policies = ",".join(json.dumps(server) + "={enabled=false}" for server in servers)
            fields.append(json.dumps(name) + "={enabled=false,mcp_servers={" + policies + "}}")
        plugin_override = "plugins={" + ",".join(fields) + "}"
        report["child_capability_scope"] = {
            "configured_other_mcp_disabled": True,
            "configured_and_cached_plugins_disabled": len(plugins),
            "plugin_mcp_servers_disabled": sum(len(servers) for servers in plugins.values()),
            "apps_disabled": True,
            "scope": "Only this disposable app-server process; no policy/global file changes",
        }
        app = AppServer(
            codex,
            workspace,
            environment,
            root,
            [server_override, plugin_override, "features.apps=false"],
        )
        app.rpc(
            "initialize", {"clientInfo": {"name": "clef_windows_gui_verification", "version": "1"}}
        )
        app.send({"method": "initialized"})
        catalog = app.rpc("skills/list", {"cwds": [str(workspace)], "forceReload": True})
        found = [skill for group in catalog.get("data", []) for skill in group.get("skills", [])]
        for name in guides:
            matches = [
                skill for skill in found if skill.get("name") == name and skill.get("enabled")
            ]
            if len(matches) != 1 or not os.path.samefile(
                matches[0]["path"], layout["root"] / name / "SKILL.md"
            ):
                raise RuntimeError("Native discovery did not uniquely bind the installed guide")
        selected_entry = dict(entry)
        selected_entry["env"] = dict(entry.get("env", {}), **private_environment)
        # Keep the managed command text exactly, including its lexical .. segment.
        selected_entry["enabled_tools"] = sorted(TOOLS)
        # Match the canonical CLI adapter's whole-map merge: dotted names are
        # actual server names, not configuration path segments to reinterpret.
        overrides = {
            "mcp_servers": {
                **{
                    name: {"enabled": False}
                    for name in config.get("mcp_servers", {})
                    if name != "clef-use"
                },
                "clef-use": selected_entry,
            }
        }
        bounds = (
            "Only the disposable Continue/Confirm foreground GUI is authorized. "
            "Read the complete installed clef-use SKILL.md before using its tools. "
            "Call computer_capabilities(detail=true) to discover current versions and schemas. "
            "Submit exactly one computer_run "
            "with the exact requested goal/condition, max_steps=8, confidence_threshold=0.9, "
            "execution_mode=AUTO and no operation, visual_intent, text_inputs or pointer_inputs. "
            "After run, call computer_observe with that returned session_id and refresh=true. "
            "Report returned status honestly, including NEEDS_REPLAN or LOW_CONFIDENCE. "
            "Do not retry, continue, change thresholds or use another GUI tool. "
            "Shell commands are permitted only to read installed public skill bodies/references. "
            "Do not read controller files, diagnostic endpoints/readbacks, auth/config, source, "
            "environment, user files or screenshots; do not send native input through shell. "
            "Do not write files or alter policies. Only abort/status your own returned session."
        )
        started = app.rpc(
            "thread/start",
            {
                "cwd": str(workspace),
                "ephemeral": True,
                "config": overrides,
                "developerInstructions": bounds,
            },
        )
        thread_id = started["thread"]["id"]
        report["resolved_thread_fields"] = {
            name: started.get(name, "NOT_EXPORTED")
            for name in ("model", "modelProvider", "approvalPolicy", "sandbox")
        }
        if started["thread"].get("ephemeral") is not True:
            raise RuntimeError("Native thread is not ephemeral")
        if any(
            report["resolved_thread_fields"][name] == "NOT_EXPORTED"
            for name in ("approvalPolicy", "sandbox")
        ):
            raise RuntimeError("Native thread did not export resolved approval/sandbox policy")
        statuses = []
        cursor = None
        while True:
            params = {"threadId": thread_id, "detail": "full", "limit": 100}
            if cursor:
                params["cursor"] = cursor
            page = app.rpc("mcpServerStatus/list", params)
            statuses.extend(page.get("data", []))
            cursor = page.get("nextCursor")
            if not cursor:
                break
        active = [server for server in statuses if server.get("tools")]
        if len(active) != 1 or active[0].get("name") != "clef-use":
            raise RuntimeError("Thread-specific MCP isolation was not established")
        actual = {name: tool["inputSchema"] for name, tool in active[0]["tools"].items()}
        if actual != expected_schemas:
            raise RuntimeError("Native MCP schemas differ from the installed full tool contract")
        report["native_discovery"] = "PASS"
        report["schema_sha256"] = digest(actual)
        expected_run = {
            "goal": GOAL,
            "success_conditions": CONDITIONS,
            "max_steps": 8,
            "confidence_threshold": 0.9,
            "execution_mode": "AUTO",
        }

        def approve_owned_request(message):
            params = message.get("params", {})
            meta = params.get("_meta") or {}
            if (
                message.get("method") != "mcpServer/elicitation/request"
                or params.get("threadId") != thread_id
                or turn_id is None
                or params.get("turnId") != turn_id
                or params.get("serverName") != "clef-use"
                or params.get("mode") != "form"
                or params.get("requestedSchema") != {"type": "object", "properties": {}}
                or meta.get("codex_approval_kind") != "mcp_tool_call"
            ):
                return False
            run_request = params.get("message") == (
                'Allow the clef-use MCP server to run tool "computer_run"?'
            )
            observe_request = params.get("message") == (
                'Allow the clef-use MCP server to run tool "computer_observe"?'
            )
            if run_request:
                if meta.get("tool_params") != expected_run or app.approved_requests:
                    return False
            elif observe_request:
                completed = task_evidence(app.events, guides, digest(expected_schemas))
                own_result = completed.get("run") or {}
                session_id = own_result.get("session_id")
                if (
                    not session_id
                    or not completed["bounded_run"]
                    or [item["tool"] for item in app.approved_requests] != ["computer_run"]
                    or meta.get("tool_params") != {"session_id": session_id, "refresh": True}
                ):
                    return False
            else:
                return False
            foreground = native.foreground()
            pid = ctypes.c_uint32()
            return bool(
                foreground == receiver["foreground_window"]
                and native.user.GetWindowThreadProcessId(foreground, ctypes.byref(pid))
                and pid.value == receiver["pid"]
            )

        app.approve_request = approve_owned_request
        prompt = (
            "Use the installed clef-use skill on the disposable foreground GUI. "
            "Goal: " + GOAL + " Success conditions: " + json.dumps(CONDITIONS) + ". "
            "Use exactly one bounded run with max_steps=8 and confidence_threshold=0.9; "
            "then freshly observe its own session and report actual result without retry."
        )
        turn = app.rpc(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [{"type": "text", "text": prompt, "text_elements": []}],
            },
        )
        turn_id = turn["turn"]["id"]
        report["model_turns_started"] = 1
        save()
        deadline = time.monotonic() + args.timeout
        pending = [
            message
            for message in app.events
            if message.get("method") == "turn/completed"
            and message.get("params", {}).get("threadId") == thread_id
        ]
        while time.monotonic() < deadline:
            message = pending.pop(0) if pending else app.next(deadline - time.monotonic())
            if (
                message.get("method") == "turn/completed"
                and message.get("params", {}).get("threadId") == thread_id
            ):
                report["turn_status"] = message["params"]["turn"].get("status")
                turn_id = None
                break
        else:
            raise TimeoutError("Native Codex GUI turn exceeded the declared deadline")
        evidence = task_evidence(app.events, guides, digest(expected_schemas))
        report["loaded_guides"] = evidence["loaded"]
        report["tool_attempts"] = evidence["attempts"]
        report["tool_calls"] = [
            {
                "tool": call["tool"],
                "native_status": call["native_status"],
                "native_error": call["native_error"],
                "successful_response": call["payload"] is not None,
            }
            for call in evidence["calls"]
        ]
        report["runtime_result"] = evidence["run"]
        report["bounded_run"] = evidence["bounded_run"]
        report["fresh_observe_after_run"] = evidence["fresh_observe_after_run"]
        report["independent_gui_readback"] = endpoint("result")
        native_success = (
            report["independent_gui_readback"].get("stage") == 2
            and report["independent_gui_readback"].get("visible_result") == "Task complete"
            and report["independent_gui_readback"].get("clicks") == ["Continue", "Confirm"]
            and report["independent_gui_readback"].get("render_delay_ms") == 500
            and report["independent_gui_readback"].get("screenshot") == "OWNED_FOREGROUND"
            and not report["independent_gui_readback"].get("input_attempts")
        )
        report["independent_task_complete"] = native_success
        passed = (
            report["turn_status"] == "completed"
            and evidence["bounded_run"]
            and evidence["fresh_observe_after_run"]
            and evidence["run"]
            and evidence["run"].get("status") == "COMPLETED"
            and native_success
        )
        report["status"] = "PASSED" if passed else "FAILED"
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(redact(str(exc)))}
    finally:
        cleanup = {}
        if app:
            report["blocked_native_requests"] = app.blocked_requests
            report["approved_native_requests"] = app.approved_requests
        try:
            client = RuntimeClient(start=False)
            if (state / "endpoint.json").exists():
                if client._send("health", {}).get("busy"):
                    client._send("abort", {})
                deadline = time.monotonic() + 15
                while (state / "endpoint.json").exists() and time.monotonic() < deadline:
                    if not client._send("health", {}).get("busy"):
                        client._send("shutdown_idle", {})
                        break
                    time.sleep(0.1)
                while (state / "endpoint.json").exists() and time.monotonic() < deadline:
                    time.sleep(0.1)
            cleanup["endpoint_removed"] = not (state / "endpoint.json").exists()
        except Exception as exc:
            cleanup["runtime_error"] = type(exc).__name__
        if app:
            try:
                if turn_id:
                    app.rpc(
                        "turn/interrupt",
                        {"threadId": thread_id, "turnId": turn_id},
                        stop_on_request=False,
                    )
                if thread_id:
                    unsubscribed = app.rpc(
                        "thread/unsubscribe", {"threadId": thread_id}, stop_on_request=False
                    )
                    cleanup["unsubscribe_status"] = unsubscribed.get("status")
                    cleanup["thread_unsubscribed"] = unsubscribed.get("status") == "unsubscribed"
            except Exception as exc:
                cleanup["thread_error"] = type(exc).__name__
            app.close()
            cleanup["app_server_exited"] = app.process.poll() is not None
            if "runtime_result" not in report and "guides" in locals():
                partial = task_evidence(app.events, guides, digest(expected_schemas))
                report["loaded_guides"] = partial["loaded"]
                report["tool_attempts"] = partial["attempts"]
                report["runtime_result"] = partial["run"]
        if gui:
            try:
                if gui.poll() is None:
                    if "independent_gui_readback" not in report:
                        report["independent_gui_readback"] = endpoint("result")
                        readback = report["independent_gui_readback"]
                        report["independent_task_complete"] = (
                            readback.get("stage") == 2
                            and readback.get("visible_result") == "Task complete"
                        )
                    endpoint("finish")
                    gui.wait(timeout=20)
                cleanup["gui_exit_code"] = gui.returncode
            except Exception as exc:
                cleanup["gui_error"] = type(exc).__name__
                if gui.poll() is None:
                    gui.terminate()
                    gui.wait(timeout=5)
            cleanup["owned_gui_process_exited"] = gui.poll() is not None
        for stream in gui_streams:
            stream.close()
        observer_stop.set()
        if observer is not None:
            observer.join(timeout=2)
        if "previous_pointer" in locals():
            with native.physical_coordinates():
                known = native.user.GetCursorPos(ctypes.byref(point))
            cleanup["pointer_restored"] = bool(known and (point.x, point.y) == previous_pointer)
            cleanup["foreground_restored"] = native.foreground() == previous
            cleanup["inputs_released"] = not any(
                native.user.GetAsyncKeyState(vk) & 0x8000 for vk in range(1, 256)
            )
        if config_path and original_config is not None:
            cleanup["global_config_bytes_preserved"] = config_path.read_bytes() == original_config
        report["cleanup"] = cleanup
        if "private_worker_archive" in report:
            report["private_worker_archive"].update(
                hook_receipts=len(list(archive.glob("hook-*.json"))),
                capture_receipts=len(list(archive.glob("capture-*.json"))),
                worker_requests=len(list(archive.glob("*-request.json"))),
                worker_replies=len(list(archive.glob("*-reply.json"))),
            )
        report["private_artifact_sha256"] = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.glob("*-private-*")
            if path.is_file()
        }
        if report["status"] == "PASSED" and (
            not all(
                cleanup.get(name)
                for name in (
                    "endpoint_removed",
                    "thread_unsubscribed",
                    "app_server_exited",
                    "owned_gui_process_exited",
                    "pointer_restored",
                    "foreground_restored",
                    "inputs_released",
                    "global_config_bytes_preserved",
                )
            )
            or cleanup.get("gui_exit_code") != 0
            or any(name.endswith("_error") for name in cleanup)
        ):
            report["status"] = "FAILED"
        save()
        if old_state is None:
            os.environ.pop("CLEF_USE_STATE_DIR", None)
        else:
            os.environ["CLEF_USE_STATE_DIR"] = old_state
    print(
        json.dumps(
            {
                name: report.get(name)
                for name in (
                    "status",
                    "runtime_version",
                    "turn_status",
                    "independent_task_complete",
                    "error",
                    "cleanup",
                )
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "PASSED" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--fixture-script",
        type=Path,
        default=Path(__file__).with_name("windows_model_gui_agent.py"),
    )
    parser.add_argument("--timeout", type=int, default=900)
    raise SystemExit(main(parser.parse_args()))

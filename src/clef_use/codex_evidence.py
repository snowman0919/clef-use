"""Bind CLI guide reads to native recording and model-facing delivery.

This is verification evidence, never input authorization. Unknown or ambiguous
recording shapes cannot prove a load.
"""

from __future__ import annotations

import json
import os
import re
import shlex
from collections import Counter, defaultdict
from pathlib import Path, PureWindowsPath
from urllib.parse import unquote, urlsplit


def local_path(value: str) -> Path:
    if not isinstance(value, str):
        raise ValueError("native Codex path is not a string")
    if value.startswith("file:"):
        uri = urlsplit(value)
        if uri.scheme != "file" or uri.netloc not in ("", "localhost") or uri.query or uri.fragment:
            raise ValueError("native Codex cwd is not a local file URI")
        if re.search(r"%(?![a-fA-F0-9]{2})", uri.path):
            raise ValueError("native Codex cwd has invalid URI escaping")
        value = unquote(uri.path, errors="strict")
        if os.name == "nt" and len(value) > 2 and value[0] == "/" and value[2] == ":":
            value = value[1:]
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("native Codex cwd is not absolute")
    return path.resolve()


def _reader_paths(argv: list[str], cwd: Path) -> set[Path]:
    """Recognize literal cat or PowerShell Get-Content without changed cwd."""
    shell = PureWindowsPath(argv[0]).name.casefold() if argv else ""
    if shell in ("pwsh", "pwsh.exe", "powershell", "powershell.exe"):
        index = next(
            (i for i, arg in enumerate(argv) if arg.casefold() in ("-command", "-c")), None
        )
        if (
            index is None
            or index != len(argv) - 2
            or any(
                arg.casefold() not in ("-noprofile", "-nologo", "-noninteractive")
                for arg in argv[1:index]
            )
        ):
            return set()
        try:
            tokens = shlex.split(argv[-1], posix=False)
        except ValueError:
            return set()
        if not tokens or tokens[0].casefold() != "get-content":
            return set()
        flags = [token.casefold() for token in tokens[1:] if token.startswith("-")]
        paths = [token for token in tokens[1:] if not token.startswith("-")]
        if (
            len(paths) != 1
            or len(flags) != len(set(flags))
            or any(flag not in ("-raw", "-literalpath", "-path") for flag in flags)
            or ("-literalpath" in flags and "-path" in flags)
        ):
            return set()
        path = paths[0]
        quoted = len(path) >= 2 and path[0] == path[-1] and path[0] in ("'", '"')
        quote = path[0] if quoted else None
        path = path[1:-1] if quoted else path
        if not path or any(char in path for char in "`\n") or (quote != "'" and "$" in path):
            return set()
        if not quoted and any(char in path for char in ";&|<>()"):
            return set()
        if "-literalpath" not in flags and any(char in path for char in "*?[]~"):
            return set()
        if (
            "-noprofile" not in [arg.casefold() for arg in argv[1:index]]
            and not Path(path).is_absolute()
        ):
            return set()
        return {(cwd / path).resolve()}
    shell_reader = False
    if len(argv) == 3 and Path(argv[0]).name in ("sh", "bash", "zsh") and argv[1] in ("-c", "-lc"):
        shell_reader = True
        # No expansion, compound commands, redirection or changed shell cwd.
        if any(char in argv[2] for char in "$`;&|<>\n*?{}[]~"):
            return set()
        try:
            argv = shlex.split(argv[2])
        except ValueError:
            return set()
    if not argv or Path(argv[0]).name != "cat":
        return set()
    args = argv[1:]
    if args[:1] == ["--"]:
        args = args[1:]
    if not args or any(path.startswith("-") for path in args):
        return set()
    # Native cwd describes shell launch, not cwd after startup files. Relative
    # operands need a direct reader; do not guess a login shell's final cwd.
    if shell_reader and any(not Path(path).is_absolute() for path in args):
        return set()
    return {(cwd / path).resolve() for path in args}


def model_texts(output) -> list[str]:
    """Read actual text blocks and their JSON transport layers, never base64."""
    texts = []

    def visit(value, depth):
        if depth > 8:
            return
        if isinstance(value, str):
            texts.append(value)
            try:
                decoded = json.loads(value)
            except ValueError:
                return
            if not isinstance(decoded, str):
                visit(decoded, depth + 1)
        elif isinstance(value, dict):
            for child in value.values():
                visit(child, depth + 1)
        elif isinstance(value, list):
            for child in value:
                visit(child, depth + 1)

    for block in output if isinstance(output, list) else []:
        if isinstance(block, dict) and block.get("type") == "input_text":
            visit(block.get("text"), 0)
    return texts


def _signature(item, native=False):
    if not isinstance(item, dict) or item.get("status") not in (
        "completed",
        "failed",
        "in_progress",
    ):
        raise ValueError("Codex execution has invalid status")
    kind = item.get("type")
    if kind in ("CommandExecution", "command_execution"):
        command = item.get("command")
        if native:
            if not isinstance(command, list) or not all(isinstance(arg, str) for arg in command):
                raise ValueError("native Codex command argv is invalid")
            command = shlex.join(command)
        return (
            "command",
            command,
            item.get("aggregated_output"),
            item.get("exit_code"),
            item.get("status"),
        )
    if kind in ("McpToolCall", "mcp_tool_call"):
        result = item.get("result")
        if isinstance(result, dict):
            result = {
                "content": result.get("content"),
                "structured_content": result.get(
                    "structuredContent" if native else "structured_content"
                ),
            }
        return (
            "mcp",
            item.get("server"),
            item.get("tool"),
            json.dumps(item.get("arguments"), sort_keys=True),
            json.dumps(result, sort_keys=True),
            item.get("status"),
        )
    return None


def _stdout_visible(output, stdout: str, exit_code: int) -> bool:
    def matches(value, depth=0):
        if depth > 8:
            return False
        if isinstance(value, dict):
            if "output" in value and "exit_code" in value:
                return (
                    value["output"] == stdout
                    and type(value["exit_code"]) is int
                    and value["exit_code"] == exit_code
                )
            return any(matches(child, depth + 1) for child in value.values())
        if isinstance(value, list):
            return any(matches(child, depth + 1) for child in value)
        return False

    for block in output if isinstance(output, list) else []:
        if not isinstance(block, dict) or block.get("type") != "input_text":
            continue
        text = block.get("text")
        if text == stdout:
            return True
        try:
            if matches(json.loads(text)):
                return True
        except (TypeError, ValueError):
            continue
    return False


def recorded_items(records: list[dict], events: list[dict], cwd: Path) -> dict:
    if not all(isinstance(record, dict) for record in records) or not all(
        isinstance(event, dict) for event in events
    ):
        raise ValueError("native Codex evidence is not an event sequence")
    threads = [event.get("thread_id") for event in events if event.get("type") == "thread.started"]
    meta = [record.get("payload") for record in records if record.get("type") == "session_meta"]
    if (
        len(threads) != 1
        or len(meta) != 1
        or not isinstance(meta[0], dict)
        or meta[0].get("id") != threads[0]
        or local_path(meta[0].get("cwd")) != cwd.resolve()
    ):
        raise ValueError("native Codex recording does not match selected session")
    calls = {}
    outputs = {}
    native = []
    native_turns = set()
    completed_turns = []
    started_turns = []
    for index, record in enumerate(records):
        payload = record.get("payload", {})
        if not isinstance(payload, dict):
            raise ValueError("native Codex recording payload is invalid")
        if record.get("type") == "event_msg" and payload.get("type") in (
            "task_started",
            "task_complete",
        ):
            turn = payload.get("turn_id")
            if not isinstance(turn, str):
                raise ValueError("native Codex turn identity is missing")
            (started_turns if payload["type"] == "task_started" else completed_turns).append(
                (index, turn)
            )
        if record.get("type") == "response_item" and payload.get("type") in (
            "custom_tool_call",
            "custom_tool_call_output",
        ):
            target = calls if payload["type"] == "custom_tool_call" else outputs
            identifier = payload.get("call_id")
            if not isinstance(identifier, str) or identifier in target:
                raise ValueError("native Codex call identity is ambiguous")
            target[identifier] = (index, payload)
        if record.get("type") == "event_msg" and payload.get("type") == "item_completed":
            if payload.get("thread_id") != threads[0]:
                raise ValueError("native Codex recording includes a foreign thread")
            item = payload.get("item", {})
            if not isinstance(item, dict):
                raise ValueError("native Codex completed item is invalid")
            if item.get("type") in ("CommandExecution", "McpToolCall"):
                native.append((index, item))
                native_turns.add(payload.get("turn_id"))
    if (
        len(started_turns) != 1
        or len(completed_turns) != 1
        or started_turns[0][1] != completed_turns[0][1]
        or native_turns - {started_turns[0][1]}
    ):
        raise ValueError("native Codex rollout does not prove turn completion")
    turn_start, turn_end = started_turns[0][0], completed_turns[0][0]
    if turn_start >= turn_end or any(
        not turn_start < index < turn_end
        for index in [
            *(index for index, _ in native),
            *(index for index, _ in calls.values()),
            *(index for index, _ in outputs.values()),
        ]
    ):
        raise ValueError("native Codex execution is outside the completed turn")
    spans = [
        (start, outputs[identifier][0], outputs[identifier][1].get("output"))
        for identifier, (start, call) in calls.items()
        if call.get("name") == "exec" and identifier in outputs and start < outputs[identifier][0]
    ]
    completed = [
        event["item"]
        for event in events
        if event.get("type") == "item.completed"
        and event.get("item", {}).get("type") in ("command_execution", "mcp_tool_call")
    ]
    bindings = []
    native_signatures = defaultdict(list)
    for index, candidate in native:
        native_signatures[_signature(candidate, True)].append((index, candidate))
    cli_signatures = Counter(_signature(item) for item in completed)
    for item in completed:
        signature = _signature(item)
        matches = native_signatures[signature]
        if len(matches) != 1 or cli_signatures[signature] != 1:
            raise ValueError("native Codex execution is not uniquely reflected in CLI output")
        index, candidate = matches[0]
        enclosing = [span for span in spans if span[0] < index < span[1]]
        if len(enclosing) != 1:
            raise ValueError("native Codex execution has no unique model-facing response")
        bindings.append((item, candidate, enclosing[0]))
    if len(bindings) != len(native):
        raise ValueError("native Codex recording includes unreported execution")
    runtime_starts = [
        span[0]
        for item, _, span in bindings
        if item["type"] == "mcp_tool_call"
        and item.get("server") == "clef-use"
        and item.get("tool") in ("computer_capabilities", "computer_status")
    ]
    result = {}
    for item, candidate, span in bindings:
        identifier = item.get("id")
        if not isinstance(identifier, str) or identifier in result:
            raise ValueError("CLI Codex execution identity is ambiguous")
        texts = model_texts(span[2])
        paths = set()
        scope_violation = None
        if candidate["type"] == "McpToolCall":
            if candidate.get("server") != "clef-use":
                scope_violation = "FOREIGN_MCP_SERVER"
            elif candidate.get("tool") not in (
                "computer_capabilities",
                "computer_status",
                "read_mcp_resource",
            ):
                scope_violation = "UNAPPROVED_RUNTIME_TOOL"
            elif candidate.get("tool") == "read_mcp_resource":
                arguments = candidate.get("arguments", {})
                uri = arguments.get("uri") if isinstance(arguments, dict) else None
                if (
                    not isinstance(arguments, dict)
                    or arguments.get("server") != "clef-use"
                    or not isinstance(uri, str)
                    or not (uri == "clef-use://api/schema" or uri.startswith("clef-use://guides/"))
                ):
                    scope_violation = "UNAPPROVED_RUNTIME_RESOURCE"
        if candidate["type"] == "CommandExecution":
            output = candidate.get("aggregated_output")
            if (
                candidate.get("status") == "completed"
                and type(candidate.get("exit_code")) is int
                and candidate["exit_code"] == 0
                and isinstance(output, str)
                and _stdout_visible(span[2], output, candidate["exit_code"])
            ):
                paths = _reader_paths(candidate["command"], local_path(candidate.get("cwd")))
        result[identifier] = {
            "paths": paths,
            "model_texts": texts,
            "before_runtime": all(span[1] < start for start in runtime_starts),
            "scope_violation": scope_violation,
            "failed": candidate.get("status") == "failed"
            or bool(candidate.get("error"))
            or (
                isinstance(candidate.get("result"), dict)
                and candidate["result"].get("isError") is True
            )
            or scope_violation is not None,
        }
    return result

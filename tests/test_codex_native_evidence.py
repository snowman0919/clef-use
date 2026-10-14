"""Consumer boundaries for clearly controlled native-recording fixtures."""

import copy
import json
import shlex

import pytest

from clef_use.codex_evidence import local_path, recorded_items

THREAD = "00000000-0000-0000-0000-000000000001"
BODY = "# Guide\nRead current capabilities before planning a bounded GUI task.\n"


def recorded_case(tmp_path):
    guide = tmp_path / ".agents/skills/clef-use/SKILL.md"
    guide.parent.mkdir(parents=True)
    guide.write_text(BODY)
    command = ["/bin/cat", ".agents/skills/clef-use/SKILL.md"]
    shell = {
        "type": "CommandExecution",
        "id": "native-shell",
        "command": command,
        "cwd": tmp_path.as_uri(),
        "status": "completed",
        "exit_code": 0,
        "aggregated_output": BODY,
        "parsed_cmd": [{"type": "read", "path": ".agents/skills/clef-use/SKILL.md"}],
    }
    payload = {"content": [{"type": "text", "text": '{"runtime_version":"current"}'}]}
    mcp = {
        "type": "McpToolCall",
        "id": "native-mcp",
        "server": "clef-use",
        "tool": "computer_capabilities",
        "arguments": {},
        "status": "completed",
        "result": {**payload, "isError": False},
    }

    def event(item):
        return {
            "type": "event_msg",
            "payload": {
                "type": "item_completed",
                "thread_id": THREAD,
                "turn_id": "turn",
                "item": item,
            },
        }

    def call(identity):
        return {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "name": "exec",
                "call_id": identity,
                "input": "native JavaScript fixture",
            },
        }

    def output(identity, value):
        return {
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call_output",
                "call_id": identity,
                "output": [{"type": "input_text", "text": json.dumps(value)}],
            },
        }

    records = [
        {"type": "session_meta", "payload": {"id": THREAD, "cwd": str(tmp_path)}},
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "turn"}},
        call("read"),
        event(shell),
        output("read", {"exit_code": 0, "output": BODY}),
        call("runtime"),
        event(mcp),
        output("runtime", payload),
        {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "turn"}},
    ]
    events = [
        {"type": "thread.started", "thread_id": THREAD},
        {
            "type": "item.completed",
            "item": {
                "type": "command_execution",
                "id": "cli-shell",
                "command": shlex.join(command),
                "status": "completed",
                "exit_code": 0,
                "aggregated_output": BODY,
            },
        },
        {
            "type": "item.completed",
            "item": {
                "type": "mcp_tool_call",
                "id": "cli-mcp",
                "server": "clef-use",
                "tool": "computer_capabilities",
                "arguments": {},
                "status": "completed",
                "result": {**payload, "structured_content": None},
            },
        },
    ]
    return records, events, guide


def test_relative_read_requires_native_cwd_and_full_model_delivery(tmp_path):
    records, events, guide = recorded_case(tmp_path)
    result = recorded_items(records, events, tmp_path)
    assert result["cli-shell"]["paths"] == {guide.resolve()}
    assert result["cli-shell"]["before_runtime"] is True
    assert BODY in result["cli-shell"]["model_texts"]


@pytest.mark.parametrize("fault", ["truncated", "wrong_exit", "no_delivery"])
def test_execution_output_without_matching_model_response_cannot_prove_load(tmp_path, fault):
    records, events, _ = recorded_case(tmp_path)
    response = records[4]["payload"]
    response["output"] = (
        []
        if fault == "no_delivery"
        else [
            {
                "type": "input_text",
                "text": json.dumps(
                    {
                        "exit_code": 1 if fault == "wrong_exit" else 0,
                        "output": BODY[:10] if fault == "truncated" else BODY,
                    }
                ),
            }
        ]
    )
    assert recorded_items(records, events, tmp_path)["cli-shell"]["paths"] == set()


def test_native_read_in_other_cwd_does_not_prove_selected_file(tmp_path):
    records, events, guide = recorded_case(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    records[3]["payload"]["item"]["cwd"] = other.as_uri()
    assert guide.resolve() not in recorded_items(records, events, tmp_path)["cli-shell"]["paths"]


def test_buffered_guide_then_runtime_in_same_exec_does_not_prove_read_before_invoke(tmp_path):
    records, events, guide = recorded_case(tmp_path)
    # The command completes first in CLI, but its body reaches the model only
    # after the same exec calls capabilities. Completion order alone is false proof.
    records.pop(5)
    records.pop(4)
    records[5]["payload"]["call_id"] = "read"
    records[5]["payload"]["output"].append(
        {"type": "input_text", "text": json.dumps({"exit_code": 0, "output": BODY})}
    )
    result = recorded_items(records, events, tmp_path)
    assert result["cli-shell"]["paths"] == {guide.resolve()}
    assert result["cli-shell"]["before_runtime"] is False


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate_native",
        "duplicate_cli",
        "foreign_thread",
        "foreign_session",
        "missing_turn_end",
        "early_turn_end",
        "duplicate_turn_start",
        "duplicate_turn_end",
        "late_turn_start",
        "output_after_turn_end",
        "overlapping_exec",
    ],
)
def test_ambiguous_foreign_or_incomplete_recording_is_rejected(tmp_path, fault):
    records, events, _ = recorded_case(tmp_path)
    if fault == "duplicate_native":
        records.insert(4, copy.deepcopy(records[3]))
    elif fault == "duplicate_cli":
        events.append(copy.deepcopy(events[1]))
    elif fault == "foreign_thread":
        records[3]["payload"]["thread_id"] = "foreign"
    elif fault == "foreign_session":
        records[0]["payload"]["cwd"] = str(tmp_path.parent)
    elif fault == "missing_turn_end":
        records.pop()
    elif fault == "early_turn_end":
        records.insert(2, records.pop())
    elif fault == "duplicate_turn_start":
        records.insert(2, copy.deepcopy(records[1]))
    elif fault == "duplicate_turn_end":
        records.append(copy.deepcopy(records[-1]))
    elif fault == "late_turn_start":
        records.insert(4, records.pop(1))
    elif fault == "output_after_turn_end":
        records.insert(7, records.pop())
    else:
        records.insert(
            3,
            {
                "type": "response_item",
                "payload": {"type": "custom_tool_call", "name": "exec", "call_id": "parallel"},
            },
        )
        records.insert(
            6,
            {
                "type": "response_item",
                "payload": {"type": "custom_tool_call_output", "call_id": "parallel", "output": []},
            },
        )
    with pytest.raises(ValueError):
        recorded_items(records, events, tmp_path)


@pytest.mark.parametrize(
    "inner",
    [
        "cat .agents/skills/clef-use/SKILL.md; cd other",
        "cat .agents/skills/clef-use/SKILL.md | cat",
        "cat $GUIDE",
        "cat *.md",
        "cat /owned/[a]/.agents/skills/clef-use/SKILL.md",
    ],
)
def test_compound_or_expanded_shell_read_cannot_borrow_native_cwd(tmp_path, inner):
    records, events, _ = recorded_case(tmp_path)
    argv = ["/bin/sh", "-c", inner]
    records[3]["payload"]["item"]["command"] = argv
    events[1]["item"]["command"] = shlex.join(argv)
    assert recorded_items(records, events, tmp_path)["cli-shell"]["paths"] == set()


@pytest.mark.parametrize("shell", ["/bin/sh", "/bin/bash", "/usr/bin/zsh"])
@pytest.mark.parametrize("mode", ["-c", "-lc"])
def test_relative_shell_reader_does_not_infer_cwd_after_startup(tmp_path, shell, mode):
    records, events, _ = recorded_case(tmp_path)
    argv = [shell, mode, "cat .agents/skills/clef-use/SKILL.md"]
    records[3]["payload"]["item"]["command"] = argv
    events[1]["item"]["command"] = shlex.join(argv)
    assert recorded_items(records, events, tmp_path)["cli-shell"]["paths"] == set()


def test_local_file_uri_decodes_once_with_spaces_unicode_and_literal_percent(tmp_path):
    path = tmp_path / "space \u97d3\u6587 %2F"
    path.mkdir()
    assert local_path(path.as_uri()) == path.resolve()


@pytest.mark.parametrize(
    "uri",
    [
        "file://remote/work",
        "file:///work?cwd=other",
        "file:///work#other",
        "file:///work%ZZ",
        "file:relative",
        "app://work",
        "relative",
    ],
)
def test_nonlocal_or_ambiguous_uri_cannot_supply_reader_origin(uri):
    with pytest.raises(ValueError):
        local_path(uri)


def test_native_mcp_error_is_retained_when_cli_projection_omits_error_flag(tmp_path):
    records, events, _ = recorded_case(tmp_path)
    records[6]["payload"]["item"]["result"]["isError"] = True
    assert recorded_items(records, events, tmp_path)["cli-mcp"]["failed"] is True


@pytest.mark.parametrize(
    "shell",
    ["pwsh", "powershell.exe", r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"],
)
def test_literal_powershell_read_binds_native_cwd_and_model_delivery(tmp_path, shell):
    records, events, guide = recorded_case(tmp_path)
    argv = [
        shell,
        "-NoProfile",
        "-Command",
        "Get-Content -Raw -LiteralPath '.agents/skills/clef-use/SKILL.md'",
    ]
    records[3]["payload"]["item"]["command"] = argv
    events[1]["item"]["command"] = shlex.join(argv)
    assert recorded_items(records, events, tmp_path)["cli-shell"]["paths"] == {guide.resolve()}


@pytest.mark.parametrize(
    "inner",
    [
        "Get-Content -Raw $guide",
        "Get-Content -Raw '*.md'",
        "Get-Content -LiteralPath 'guide'; Set-Location other",
        "Get-Content 'guide' | Write-Output",
    ],
)
def test_dynamic_or_compound_powershell_cannot_prove_literal_reader_origin(tmp_path, inner):
    records, events, _ = recorded_case(tmp_path)
    argv = ["pwsh", "-Command", inner]
    records[3]["payload"]["item"]["command"] = argv
    events[1]["item"]["command"] = shlex.join(argv)
    assert recorded_items(records, events, tmp_path)["cli-shell"]["paths"] == set()

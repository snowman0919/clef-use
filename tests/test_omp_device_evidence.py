"""Evidence-parser behavior for native OMP device dispatch, not a harness proof."""

import copy
import hashlib
import json

import pytest

from clef_use import integrations
from clef_use.capabilities import capabilities, digest, skill_root, tool_schemas


@pytest.fixture
def device_case(tmp_path):
    root = tmp_path / "skills"
    guide = root / "clef-use" / "SKILL.md"
    guide.parent.mkdir(parents=True)
    guide.write_bytes((skill_root() / "clef-use" / "SKILL.md").read_bytes())
    schemas = tool_schemas()
    schemas = {name: schemas[name] for name in ("computer_capabilities", "computer_status")}
    payload = capabilities(detail=True)
    payload.update(
        tools=list(schemas), schemas=schemas, schema_sha256=digest(schemas), read_only_facade=True
    )
    manifest = {
        "release": payload["runtime_version"],
        "schema_sha256": digest(tool_schemas()),
        "skills": {
            "clef-use": {"files": {"SKILL.md": hashlib.sha256(guide.read_bytes()).hexdigest()}}
        },
    }
    target = "mcp__clef_use_computer_capabilities"
    content = [{"type": "text", "text": json.dumps(payload)}]
    load = [
        {
            "type": "tool_execution_start",
            "toolName": "read",
            "toolCallId": "guide",
            "args": {"path": "skill://clef-use"},
        },
        {
            "type": "tool_execution_end",
            "toolName": "read",
            "toolCallId": "guide",
            "result": {
                "content": [{"type": "text", "text": guide.read_text().split("---", 2)[-1].strip()}]
            },
        },
    ]
    invoke = [
        {
            "type": "tool_execution_start",
            "toolName": "write",
            "toolCallId": "cap",
            "args": {"path": "xd://" + target, "content": json.dumps({"detail": True})},
        },
        {
            "type": "tool_execution_end",
            "toolName": "write",
            "toolCallId": "cap",
            "isError": False,
            "result": {
                "content": content,
                "details": {
                    "xdev": {
                        "tool": target,
                        "mode": "execute",
                        "tier": "write",
                        "args": {"detail": True},
                        "inner": {
                            "serverName": "clef-use",
                            "mcpToolName": "computer_capabilities",
                            "isError": False,
                            "rawContent": copy.deepcopy(content),
                        },
                    }
                },
            },
        },
    ]
    return {"root": root}, manifest, load, invoke, tmp_path


def evaluate(case, events):
    layout, manifest, _, _, cwd = case
    return integrations._omp_model_evidence(layout, manifest, events, "explicit", 0, cwd)


def test_bound_device_capability_after_full_guide_is_verified(device_case):
    _, _, load, invoke, _ = device_case
    result = evaluate(device_case, load + invoke)
    assert result["status"] == "PASS"
    assert result["invoked"] == ["mcp__clef_use_computer_capabilities"]


def test_native_device_intent_metadata_is_distinct_from_runtime_arguments(device_case):
    _, _, load, invoke, _ = device_case
    invoke = copy.deepcopy(invoke)
    invoke[0]["args"]["content"] = json.dumps({"detail": True, "i": "Inspect the live catalog"})
    result = evaluate(device_case, load + invoke)
    assert result["status"] == "PASS"
    assert result["invoked"] == ["mcp__clef_use_computer_capabilities"]


def test_device_invocation_before_guide_stays_failed(device_case):
    _, _, load, invoke, _ = device_case
    result = evaluate(device_case, invoke + load)
    assert result["status"] == "FAIL"
    assert result["runtime_before_guide"]


@pytest.mark.parametrize(
    "mismatch", ["path", "target", "args", "server", "inner_error", "consumer_content"]
)
def test_device_metadata_cannot_authorize_unbound_or_failed_call(device_case, mismatch):
    _, _, load, invoke, _ = device_case
    invoke = copy.deepcopy(invoke)
    native = invoke[1]["result"]["details"]["xdev"]
    if mismatch == "path":
        invoke[0]["args"]["path"] = "ordinary-file.txt"
    elif mismatch == "target":
        native["tool"] = "mcp__other_computer_capabilities"
    elif mismatch == "args":
        native["args"]["detail"] = False
    elif mismatch == "server":
        native["inner"]["serverName"] = "other"
    elif mismatch == "inner_error":
        native["inner"]["isError"] = True
    else:
        invoke[1]["result"]["content"] = [{"type": "text", "text": "{}"}]
    result = evaluate(device_case, load + invoke)
    assert result["status"] == "FAIL"
    assert not result["invoked"]


def test_denied_file_write_keeps_valid_device_case_failed(device_case):
    _, _, load, invoke, _ = device_case
    write = [
        {
            "type": "tool_execution_start",
            "toolName": "write",
            "toolCallId": "file",
            "args": {"path": "ordinary.txt", "content": "changed"},
        },
        {
            "type": "tool_execution_end",
            "toolName": "write",
            "toolCallId": "file",
            "isError": True,
            "result": {"content": [{"type": "text", "text": "Denied"}]},
        },
    ]
    result = evaluate(device_case, load + invoke + write)
    assert result["status"] == "FAIL"
    assert result["read_only_violations"] == ["write"]


def test_unpaired_write_result_cannot_hide_behind_valid_device_call(device_case):
    _, _, load, invoke, _ = device_case
    orphan = copy.deepcopy(invoke[1])
    orphan["toolCallId"] = "unpaired"
    result = evaluate(device_case, load + [orphan] + invoke)
    assert result["status"] == "FAIL"
    assert result["read_only_violations"] == ["write"]

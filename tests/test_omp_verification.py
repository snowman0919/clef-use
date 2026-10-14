"""Consumer boundaries for native OMP read-only verification policy."""

import copy
import json

import pytest

from clef_use import integrations


def test_native_approval_overlay_blocks_write_even_with_existing_allow():
    original = {"write": "allow", "bash": "allow", "unknown_plugin": "allow"}
    policy = integrations._omp_read_only_policy(original)
    assert policy["tools"]["approvalMode"] == "always-ask"
    assert all(policy["tools"]["approval"][key] == "deny" for key in original)
    assert original == {"write": "allow", "bash": "allow", "unknown_plugin": "allow"}


@pytest.mark.parametrize("restriction", ["deny", "prompt"])
def test_native_approval_overlay_preserves_restricted_read_only_tools(restriction):
    name = "mcp__clef_use_computer_capabilities"
    policy = integrations._omp_read_only_policy({name: restriction, "read": restriction})
    assert policy["tools"]["approval"][name] == restriction
    assert policy["tools"]["approval"]["read"] == restriction
    assert policy["tools"]["approval"]["write"] == "deny"


def test_native_approval_overlay_allows_only_known_probe_readers():
    policy = integrations._omp_read_only_policy({})["tools"]["approval"]
    assert {key for key, value in policy.items() if value == "allow"} == {
        "mcp__clef_use_computer_capabilities",
        "mcp__clef_use_computer_status",
    }
    assert policy["write"] == "deny"
    assert policy["read"] is None


def test_existing_read_allow_does_not_bypass_argument_sensitive_native_tiers():
    policy = integrations._omp_read_only_policy({"read": "allow"})
    assert policy["tools"]["approval"]["read"] is None


@pytest.fixture
def evidence(tmp_path):
    from clef_use.capabilities import digest, tool_schemas

    guide = tmp_path / "skills/clef-use/SKILL.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("---\nname: clef-use\n---\n# Guide\n" + "Read complete instructions.\n" * 100)
    hashes = {"SKILL.md": integrations._hash(guide.read_bytes())}
    manifest = {
        "release": "0.1.42",
        "schema_sha256": digest(tool_schemas()),
        "skills": {"clef-use": {"files": hashes}},
    }
    capability = {
        "runtime_version": manifest["release"],
        "schema_sha256": manifest["schema_sha256"],
        "guides": {"skills": {"clef-use": {"sha256": hashes}}},
    }
    events = []
    for name, args, text in [
        ("read", {"path": "skill://clef-use"}, guide.read_text()),
        ("mcp__clef_use_computer_capabilities", {}, json.dumps(capability)),
    ]:
        identity = str(len(events))
        events.extend(
            [
                {
                    "type": "tool_execution_start",
                    "toolCallId": identity,
                    "toolName": name,
                    "args": args,
                },
                {
                    "type": "tool_execution_end",
                    "toolCallId": identity,
                    "toolName": name,
                    "isError": False,
                    "result": {"content": [{"type": "text", "text": text}]},
                },
            ]
        )
    return {"root": guide.parent.parent}, manifest, events


def score(evidence, trigger="explicit", exit_code=0):
    return integrations._omp_model_evidence(
        *evidence, trigger, exit_code, evidence[0]["root"].parent
    )


def test_full_guide_and_matching_capabilities_prove_model_invocation(evidence):
    result = score(evidence)
    assert result["status"] == "PASS"
    assert result["loaded"] == ["clef-use"]
    assert result["invoked"] == ["mcp__clef_use_computer_capabilities"]


def test_relative_guide_read_uses_native_selected_project_cwd(evidence):
    evidence[2][0]["args"]["path"] = "skills/clef-use/SKILL.md"
    assert score(evidence)["status"] == "PASS"


def test_relative_gui_read_rejects_negative_trigger(evidence):
    evidence[2][0]["args"]["path"] = "skills/clef-use/SKILL.md"
    del evidence[2][2:]
    assert score(evidence, trigger="negative")["status"] == "FAIL"


def test_guide_prefix_cannot_prove_full_loading(evidence):
    evidence[2][1]["result"]["content"][0]["text"] = evidence[2][1]["result"]["content"][0]["text"][
        :500
    ]
    assert score(evidence)["status"] == "FAIL"
    assert score(evidence)["loaded"] == []


@pytest.mark.parametrize("failed", [False, True])
@pytest.mark.parametrize("exit_code", [0, 1])
def test_write_attempt_cannot_pass_or_disappear_behind_deadline(evidence, failed, exit_code):
    events = evidence[2]
    events.extend(
        [
            {
                "type": "tool_execution_start",
                "toolCallId": "write",
                "toolName": "write",
                "args": {},
            },
            {
                "type": "tool_execution_end",
                "toolCallId": "write",
                "toolName": "write",
                "isError": failed,
                "result": {"content": [{"type": "text", "text": "result"}]},
            },
        ]
    )
    result = score(evidence, exit_code=exit_code)
    assert result["status"] == "FAIL"
    assert result["read_only_violations"] == ["write"]


def test_failed_call_cannot_be_erased_by_later_success(evidence):
    call, end = copy.deepcopy(evidence[2][-2:])
    call["toolCallId"] = end["toolCallId"] = "failed"
    end["isError"] = True
    evidence[2][2:2] = [call, end]
    result = score(evidence)
    assert result["status"] == "FAIL"
    assert result["invoked"] == ["mcp__clef_use_computer_capabilities"]


def test_wrapped_error_after_success_is_still_a_failed_call(evidence):
    call, end = copy.deepcopy(evidence[2][-2:])
    call["toolCallId"] = end["toolCallId"] = "wrapped-error"
    end["result"]["content"][0]["text"] = '{"error":"invalid operation"}'
    evidence[2].extend([call, end])
    result = score(evidence)
    assert result["status"] == "FAIL"
    assert result["failed_calls"][0]["tool_call_id"] == "wrapped-error"


def test_absent_content_cannot_prove_guide_or_capability(evidence):
    evidence[2][1]["result"]["content"] = None
    evidence[2][-1]["result"]["content"] = None
    result = score(evidence)
    assert result["status"] == "FAIL"
    assert result["loaded"] == result["invoked"] == []


def test_pending_call_after_success_prevents_pass(evidence):
    evidence[2].append(
        {
            "type": "tool_execution_start",
            "toolCallId": "pending",
            "toolName": "mcp__clef_use_computer_status",
            "args": {},
        }
    )
    assert score(evidence)["status"] == "NOT_RUN"


def test_wrong_runtime_cannot_prove_capability_invocation(evidence):
    content = evidence[2][-1]["result"]["content"][0]
    payload = json.loads(content["text"])
    payload["runtime_version"] = "different"
    content["text"] = json.dumps(payload)
    assert score(evidence)["invoked"] == []

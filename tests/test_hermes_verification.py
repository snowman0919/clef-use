"""Consumer evidence boundaries for Hermes' bounded event stream and native transcript."""

import copy
import json

import pytest

from clef_use import integrations
from clef_use.capabilities import digest


@pytest.fixture
def evidence(tmp_path):
    profile = tmp_path / "profile"
    root = profile / "skills"
    guide = root / "clef-use/SKILL.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("---\nname: clef-use\n---\n# Guide\n" + "Public instructions.\n" * 400)
    schemas = {"computer_capabilities": {"type": "object"}}
    manifest = {
        "release": "0.1.40",
        "schema_sha256": digest(schemas),
        "skills": {"clef-use": {"files": {"SKILL.md": integrations._hash(guide.read_bytes())}}},
    }
    capability = {
        "runtime_version": "0.1.40",
        "schema_sha256": manifest["schema_sha256"],
        "schemas": schemas,
        "guides": {"skills": {"clef-use": {"sha256": manifest["skills"]["clef-use"]["files"]}}},
    }
    payloads = [
        (
            "load",
            "skill_view",
            {"name": "clef-use"},
            {
                "success": True,
                "_source_path": str(guide),
                "content": guide.read_text(),
            },
        ),
        ("invoke", "mcp__clef_use__computer_capabilities", {"detail": True}, capability),
    ]
    messages, events = [], [{"type": "system", "subtype": "init", "session_id": "session_1"}]
    for index, (call_id, name, arguments, payload) in enumerate(payloads):
        outer = (
            {"calls": [{"name": name, "arguments": arguments}]}
            if name.startswith("mcp__")
            else arguments
        )
        function = "tool_call" if name.startswith("mcp__") else name
        messages.extend(
            [
                {
                    "id": index * 2,
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": call_id,
                            "function": {"name": function, "arguments": json.dumps(outer)},
                        }
                    ],
                },
                {
                    "id": index * 2 + 1,
                    "role": "tool",
                    "tool_call_id": call_id,
                    "tool_name": name,
                    "content": json.dumps(payload),
                },
            ]
        )
        output = json.dumps(payload)
        events.extend(
            [
                {"type": "tool_use", "name": name, "input": arguments},
                {
                    "type": "tool_result",
                    "name": name,
                    "is_error": False,
                    "output": output[:5000] + "..." if len(output) > 5000 else output,
                },
            ]
        )
    events.append({"type": "result", "session_id": "session_1", "exit_code": 0})
    layout = {"config": profile / "config.yaml", "root": root, "state": profile / "state"}
    return layout, manifest, events, {"id": "session_1", "messages": messages}


def score(evidence):
    return integrations._hermes_model_evidence(*evidence, "explicit")


def test_full_canonical_response_recovers_truncated_stream(evidence):
    result = score(evidence)
    assert result["status"] == "PASS"
    assert result["loaded"] == ["clef-use"]
    assert result["invoked"] == ["mcp__clef_use__computer_capabilities"]


@pytest.mark.parametrize(
    "payload",
    [
        {"result": json.dumps({"error": "runtime rejected request"})},
        {"result": {"details": {"isError": True}}},
        {"result": {"runtime_version": "0.1.40"}, "structuredContent": {"error": "failed"}},
        {"result": ""},
        {},
        None,
        '{"runtime_version":',
        "...",
    ],
)
def test_wrapped_errors_empty_and_incomplete_responses_never_prove_invocation(evidence, payload):
    evidence[3]["messages"][-1]["content"] = (
        payload if isinstance(payload, str) else json.dumps(payload)
    )
    evidence[2][-2]["output"] = evidence[3]["messages"][-1]["content"]
    result = score(evidence)
    assert result["status"] != "PASS"
    assert result["invoked"] == []


@pytest.mark.parametrize(
    "mutation", ["session", "terminal", "call", "duplicate", "tool", "arguments"]
)
def test_inconsistent_native_identity_cannot_supply_evidence(evidence, mutation):
    layout, manifest, events, transcript = evidence
    if mutation == "session":
        transcript["id"] = "another_session"
    elif mutation == "terminal":
        events[-1]["session_id"] = "another_session"
    elif mutation == "call":
        transcript["messages"][-1]["tool_call_id"] = "another_call"
    elif mutation == "duplicate":
        transcript["messages"].append(copy.deepcopy(transcript["messages"][-1]))
    elif mutation == "tool":
        transcript["messages"][-1]["tool_name"] = "mcp__another__computer_capabilities"
    else:
        events[-3]["input"] = {"detail": False}
    with pytest.raises(ValueError):
        score(evidence)


def spill(evidence, path):
    message = evidence[3]["messages"][-1]
    raw = message["content"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw)
    message["content"] = (
        "<persisted-output>\nFull output saved to: " + str(path) + "\n</persisted-output>"
    )


def test_exact_profile_and_call_spillover_preserves_complete_payload(evidence):
    path = evidence[0]["config"].parent / "cache/spillover/invoke.txt"
    spill(evidence, path)
    assert score(evidence)["status"] == "PASS"


@pytest.mark.parametrize("unsafe", ["outside", "wrong_call", "symlink", "oversize"])
def test_untrusted_spillover_paths_and_excessive_responses_are_refused(evidence, unsafe, tmp_path):
    path = evidence[0]["config"].parent / "cache/spillover/invoke.txt"
    if unsafe == "outside":
        path = tmp_path / "outside/invoke.txt"
    elif unsafe == "wrong_call":
        path = path.with_name("other_call.txt")
    spill(evidence, path)
    if unsafe == "symlink":
        target = path.with_name("original.txt")
        path.rename(target)
        path.symlink_to(target)
    elif unsafe == "oversize":
        path.write_bytes(b" " * (integrations._HERMES_TRANSCRIPT_LIMIT + 1))
    with pytest.raises(ValueError):
        score(evidence)


def test_completed_error_stays_recorded_beside_success(evidence):
    layout, manifest, events, transcript = evidence
    bad_call = copy.deepcopy(transcript["messages"][-2])
    bad_call["id"] = 4
    bad_call["tool_calls"][0]["id"] = "failed"
    args = {
        "calls": [
            {
                "name": "mcp__clef_use__computer_capabilities",
                "arguments": {"operation_id": "invented"},
            }
        ]
    }
    bad_call["tool_calls"][0]["function"]["arguments"] = json.dumps(args)
    transcript["messages"].extend(
        [
            bad_call,
            {
                "id": 5,
                "role": "tool",
                "tool_call_id": "failed",
                "tool_name": "mcp__clef_use__computer_capabilities",
                "content": '{"error":"UNKNOWN_OPERATION"}',
            },
        ]
    )
    events[-1:-1] = [
        {
            "type": "tool_use",
            "name": "mcp__clef_use__computer_capabilities",
            "input": {"operation_id": "invented"},
        },
        {
            "type": "tool_result",
            "name": "mcp__clef_use__computer_capabilities",
            "is_error": True,
            "output": '{"error":"UNKNOWN_OPERATION"}',
        },
    ]
    result = score(evidence)
    assert result["status"] == "FAIL"
    assert result["invoked"] == ["mcp__clef_use__computer_capabilities"]
    assert result["failed_calls"][0]["tool_call_id"] == "failed"


@pytest.mark.parametrize("field", ["runtime_version", "schema_sha256", "schemas", "guides"])
def test_capability_response_must_match_managed_runtime_and_contract(evidence, field):
    row = evidence[3]["messages"][-1]
    payload = json.loads(row["content"])
    payload[field] = {} if field in ("schemas", "guides") else "different"
    row["content"] = json.dumps(payload)
    evidence[2][-2]["output"] = row["content"]
    assert score(evidence)["invoked"] == []


@pytest.mark.parametrize("corruption", [None, "extra_tool", "wrong_schema", "wrong_guide"])
def test_read_only_facade_uses_its_actual_schema_and_rejects_effectful_surface(
    evidence, corruption
):
    from clef_use.capabilities import tool_schemas

    row = evidence[3]["messages"][-1]
    payload = json.loads(row["content"])
    schemas = tool_schemas()
    schemas = {name: schemas[name] for name in ("computer_capabilities", "computer_status")}
    payload.update(
        read_only_facade=True,
        tools=list(schemas),
        schemas=schemas,
        schema_sha256=digest(schemas),
    )
    if corruption == "extra_tool":
        payload["tools"].append("computer_run")
    elif corruption == "wrong_schema":
        payload["schemas"]["computer_status"] = {"type": "string"}
        payload["schema_sha256"] = digest(payload["schemas"])
    elif corruption == "wrong_guide":
        payload["guides"]["skills"]["clef-use"]["sha256"]["SKILL.md"] = "different"
    row["content"] = json.dumps(payload)
    raw = row["content"]
    evidence[2][-2]["output"] = raw[:5000] + "..." if len(raw) > 5000 else raw
    result = score(evidence)
    assert result["status"] == ("PASS" if corruption is None else "FAIL")
    assert bool(result["invoked"]) == (corruption is None)


def test_structured_error_cannot_be_hidden_beside_valid_text_response(evidence):
    row = evidence[3]["messages"][-1]
    row["content"] = json.dumps(
        {"result": row["content"], "structuredContent": {"error": "failed"}}
    )
    evidence[2][-2]["output"] = row["content"]
    result = score(evidence)
    assert result["invoked"] == []
    assert result["failed_calls"][0]["tool_call_id"] == "invoke"


def test_concurrent_results_without_call_ids_or_distinguishing_content_are_ambiguous(evidence):
    events, messages = evidence[2], evidence[3]["messages"]
    call, result = copy.deepcopy(messages[-2:])
    call["id"], result["id"] = 4, 5
    call["tool_calls"][0]["id"] = result["tool_call_id"] = "second"
    messages.extend([call, result])
    events.insert(-2, copy.deepcopy(events[-3]))
    events.insert(-1, copy.deepcopy(events[-2]))
    with pytest.raises(ValueError):
        score(evidence)


@pytest.mark.parametrize("preview", ["different", "short...", "missing", "altered_prefix"])
def test_canonical_response_must_bind_to_native_stream_bytes(evidence, preview):
    if preview == "altered_prefix":
        evidence[2][2]["output"] = "x" + evidence[2][2]["output"][1:]
    else:
        evidence[2][-2]["output"] = "" if preview == "missing" else preview
    with pytest.raises(ValueError):
        score(evidence)


@pytest.mark.parametrize(
    "shape",
    [
        "non_assistant_calls",
        "calls_object",
        "empty_calls_object",
        "call_scalar",
        "function_scalar",
        "message_id",
        "result_scalar",
    ],
)
def test_malformed_canonical_messages_are_refused(evidence, shape):
    messages = evidence[3]["messages"]
    if shape == "non_assistant_calls":
        messages[-2]["role"] = "user"
    elif shape == "calls_object":
        messages[-2]["tool_calls"] = {"id": "invoke"}
    elif shape == "empty_calls_object":
        messages[-2]["tool_calls"] = {}
    elif shape == "call_scalar":
        messages[-2]["tool_calls"] = ["invoke"]
    elif shape == "function_scalar":
        messages[-2]["tool_calls"][0]["function"] = "function"
    elif shape == "message_id":
        messages[-2]["id"] = {}
    else:
        messages[-1]["content"] = {}
    with pytest.raises(ValueError):
        score(evidence)


def test_total_recovered_response_bytes_are_bounded(evidence, monkeypatch):
    monkeypatch.setattr(integrations, "_HERMES_TRANSCRIPT_LIMIT", 12_000)
    message = evidence[3]["messages"][-1]
    payload = json.loads(message["content"])
    payload["public_detail"] = "x" * 8000
    message["content"] = json.dumps(payload)
    evidence[2][-2]["output"] = message["content"][:5000] + "..."
    spill(evidence, evidence[0]["config"].parent / "cache/spillover/invoke.txt")
    with pytest.raises(ValueError):
        score(evidence)


def test_parallel_distinct_truncated_bodies_bind_to_their_native_calls(evidence):
    layout, manifest, events, transcript = evidence
    guide = layout["root"] / "clef-use-diagnostics/SKILL.md"
    guide.parent.mkdir()
    guide.write_text("---\nname: clef-use-diagnostics\n---\n# Diagnostics\n" + "Evidence.\n" * 800)
    hashes = {"SKILL.md": integrations._hash(guide.read_bytes())}
    manifest["skills"]["clef-use-diagnostics"] = {"files": hashes}
    call = copy.deepcopy(transcript["messages"][0]["tool_calls"][0])
    call["id"] = "diagnostics"
    call["function"]["arguments"] = json.dumps({"name": "clef-use-diagnostics"})
    transcript["messages"][0]["tool_calls"].append(call)
    output = json.dumps({"success": True, "_source_path": str(guide), "content": guide.read_text()})
    transcript["messages"].insert(
        2,
        {
            "id": 10,
            "role": "tool",
            "tool_call_id": "diagnostics",
            "tool_name": "skill_view",
            "content": output,
        },
    )
    events[2:2] = [
        {"type": "tool_use", "name": "skill_view", "input": {"name": "clef-use-diagnostics"}},
        {
            "type": "tool_result",
            "name": "skill_view",
            "is_error": False,
            "output": output[:5000] + "...",
        },
    ]
    payload = json.loads(transcript["messages"][-1]["content"])
    payload["guides"]["skills"]["clef-use-diagnostics"] = {"sha256": hashes}
    transcript["messages"][-1]["content"] = events[-2]["output"] = json.dumps(payload)
    result = score(evidence)
    assert result["status"] == "PASS"
    assert set(result["loaded"]) == {"clef-use", "clef-use-diagnostics"}


def test_pending_call_after_success_cannot_prove_complete_verification(evidence):
    events, messages = evidence[2], evidence[3]["messages"]
    name = "mcp__clef_use__computer_status"
    messages.append(
        {
            "id": 10,
            "role": "assistant",
            "tool_calls": [{"id": "pending", "function": {"name": name, "arguments": "{}"}}],
        }
    )
    events.insert(-1, {"type": "tool_use", "name": name, "input": {}})
    with pytest.raises(ValueError, match="inventories disagree"):
        score(evidence)


@pytest.mark.parametrize("has_result", [False, True])
@pytest.mark.parametrize("name", ["mcp__clef_use__computer_run", "skill_manage"])
def test_canonical_effectful_call_missing_from_stream_cannot_pass(evidence, has_result, name):
    messages = evidence[3]["messages"]
    messages.append(
        {
            "id": 10,
            "role": "assistant",
            "tool_calls": [{"id": "omitted", "function": {"name": name, "arguments": "{}"}}],
        }
    )
    if has_result:
        messages.append(
            {
                "id": 11,
                "role": "tool",
                "tool_call_id": "omitted",
                "tool_name": name,
                "content": '{"error":"read-only server refused"}',
            }
        )
    result = score(evidence)
    assert result["status"] == "FAIL"
    assert result["read_only_violations"] == [name]


@pytest.mark.parametrize(
    "name",
    [
        "mcp__clef_use__computer_run",
        "skill_manage",
        "mcp__clef_use__list_resources",
        "mcp__clef_use__read_resource",
        "mcp__clef_use__list_prompts",
        "mcp__clef_use__get_prompt",
    ],
)
@pytest.mark.parametrize("failed", [False, True])
def test_effectful_or_failed_protocol_attempt_cannot_pass_read_only_verification(
    evidence, name, failed
):
    events, messages = evidence[2], evidence[3]["messages"]
    messages.extend(
        [
            {
                "id": 10,
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "write",
                        "function": {
                            "name": name,
                            "arguments": json.dumps({"goal": "change desktop"}),
                        },
                    }
                ],
            },
            {
                "id": 11,
                "role": "tool",
                "tool_call_id": "write",
                "tool_name": name,
                "content": json.dumps({"error": "policy refused"} if failed else {"resources": []}),
            },
        ]
    )
    events[-1:-1] = [
        {"type": "tool_use", "name": name, "input": {"goal": "change desktop"}},
        {
            "type": "tool_result",
            "name": name,
            "is_error": failed,
            "output": json.dumps({"error": "policy refused"} if failed else {"resources": []}),
        },
    ]
    result = score(evidence)
    effectful = name.endswith("computer_run") or name == "skill_manage"
    assert result["status"] == ("FAIL" if effectful or failed else "PASS")
    assert result["read_only_violations"] == ([name] if effectful else [])
    assert name not in result["invoked"]
    if failed and not effectful:
        assert result["failed_calls"][-1]["tool"] == name

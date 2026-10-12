import json

import pytest
from PIL import Image

from clef_use.backends import decision_request
from clef_use.benchmark import FixtureDesktop
from clef_use.candidates import CandidateBuilder
from clef_use.config import Config
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import (
    BoundingBox,
    Contract,
    Decision,
    Frame,
    Observation,
    UIObject,
    VisualIntent,
)


def field(identity, left, **updates):
    return UIObject(
        id=identity,
        label="Name",
        role="input",
        bbox=BoundingBox(x1=left, y1=0.2, x2=left + 0.1, y2=0.4),
        actions={"click", "focus", "type"},
    ).model_copy(update=updates)


def test_literal_candidates_preserve_each_matching_input_through_the_decision_packet():
    objects = (field("left", 0.1), field("right", 0.7))
    observation = Observation("fields", Frame(Image.new("RGB", (100, 100))), objects)
    contract = Contract(
        goal="Enter the supplied names into the appropriate fields",
        text_inputs=[{"value": "Alice", "target_label": "Name"}, {"value": "Bob"}],
    )
    candidates = CandidateBuilder().build(observation, contract)
    actual = {(a.target, a.value) for a in candidates if a.operation == "type"}
    assert actual == {(target, value) for target in ("left", "right") for value in ("Alice", "Bob")}
    packet = json.loads(json.dumps(decision_request(observation, contract, candidates, [])))
    by_id = {obj["id"]: obj for obj in packet["state"]["objects"]}
    right = [
        action
        for action in packet["state"]["allowed_candidates"]
        if action["operation"] == "type" and action["target"] == "right"
    ]
    assert len(right) == 2
    assert all(by_id[action["target"]]["bbox"]["x1"] == 70 for action in right)


@pytest.mark.parametrize("target_label", [None, "Missing"])
def test_literal_budget_counts_matching_actionable_inputs_only(target_label):
    fields = (
        field("left", 0.1),
        field("right", 0.7),
        field("disabled", 0.3, enabled=False),
        field("readonly", 0.4, editable=False),
        field("sensitive", 0.5, sensitive=True),
        field("occluded", 0.6, occluded=True),
    )
    buttons = tuple(
        field(str(i), 0.1, role="button", actions=frozenset({"click"})) for i in range(12)
    )
    observation = Observation("fields", Frame(Image.new("RGB", (100, 100))), buttons + fields)
    builder = CandidateBuilder(limit=12)
    candidates = builder.build(
        observation,
        Contract(
            goal="Enter a name", text_inputs=[{"value": "Alice", "target_label": target_label}]
        ),
    )
    actual = {(a.target, a.value) for a in candidates if a.operation == "type"}
    assert actual == ({("left", "Alice"), ("right", "Alice")} if target_label is None else set())
    if target_label is not None:
        assert len([a for a in candidates if a.operation == "click"]) == 12


@pytest.mark.parametrize(
    "field_count,literal_count,limit,missing", [(13, 1, 12, 1), (5, 10, 48, 2)]
)
def test_excess_literal_alternatives_request_replanning_before_model_or_input(
    field_count, literal_count, limit, missing
):
    class Desktop(FixtureDesktop):
        def parse(self, image):
            return tuple(field(str(i), 0.1) for i in range(field_count))

        def decide(self, *args):
            pytest.fail("a truncated text roster must not reach the model")

        def execute(self, *args):
            pytest.fail("a truncated text roster must not send input")

    desktop = Desktop()
    runtime = SessionRuntime(
        desktop, desktop, desktop, desktop, Config(max_candidates=limit, activity_overlay=False)
    )
    session = Session(
        Contract(
            goal="Enter name", text_inputs=[{"value": f"Name {i}"} for i in range(literal_count)]
        )
    )
    result = runtime.execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert "text alternatives" in result["reason"]
    diagnostics = session.history[-1]["candidate_diagnostics"]
    assert diagnostics["text_proposals_before_limit"] == field_count * literal_count
    assert diagnostics["text_proposals_after_limit"] == limit
    assert diagnostics["text_proposals_truncated"] == missing
    assert session.steps == 0


@pytest.mark.parametrize("operation,count", [("click", 4), ("double_click", 4), ("scroll", 8)])
def test_explicit_primitive_retains_observed_targets_before_literal_budget(operation, count):
    class Assessment:
        def decide(self, *args):
            return Decision(mode="NEEDS_REPLAN", confidence=1)

    objects = tuple(
        field(
            str(i),
            0.1 + i * 0.2,
            actions=frozenset({"click", "double_click", "focus", "type", "scroll"}),
        )
        for i in range(4)
    )
    observation = Observation("fields", Frame(Image.new("RGB", (100, 100))), objects)
    contract = Contract(
        goal="Activate Name using the requested primitive; literals are supplied for later entry",
        execution_mode="STRUCTURED",
        visual_intent=VisualIntent(query="Name", operation=operation),
        text_inputs=[{"value": str(i)} for i in range(12)],
    )
    runtime = SessionRuntime(None, None, Assessment(), None, Config())
    row = {}
    candidates, _ = runtime._choose(observation, Session(contract), [], row)
    assert {candidate.target for candidate in candidates} == {"0", "1", "2", "3"}
    assert [candidate.operation for candidate in candidates] == [operation] * count
    diagnostics = row["candidate_diagnostics"]
    assert diagnostics["proposals_before_limit"] == count
    assert diagnostics["proposals_after_limit"] == count
    assert diagnostics["text_proposals_before_limit"] == 0
    assert diagnostics["text_proposals_truncated"] == 0


def test_explicit_double_click_never_grants_unobserved_capability():
    observation = Observation("fields", Frame(Image.new("RGB", (100, 100))), (field("0", 0.1),))
    candidates = CandidateBuilder().build(
        observation,
        Contract(
            goal="Activate Name", visual_intent=VisualIntent(query="Name", operation="double_click")
        ),
    )
    assert not candidates


def test_no_intent_preserves_every_literal_target_pair_at_default_budget():
    objects = tuple(field(str(i), 0.1 + i * 0.2) for i in range(4))
    observation = Observation("fields", Frame(Image.new("RGB", (100, 100))), objects)
    contract = Contract(
        goal="Enter the supplied names", text_inputs=[{"value": str(i)} for i in range(12)]
    )
    candidates = CandidateBuilder().build(observation, contract)
    assert {(candidate.target, candidate.value) for candidate in candidates} == {
        (str(target), str(value)) for target in range(4) for value in range(12)
    }
    assert all(candidate.operation == "type" for candidate in candidates)

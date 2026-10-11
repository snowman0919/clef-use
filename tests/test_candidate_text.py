import json

import pytest
from PIL import Image

from clef_use.backends import decision_request
from clef_use.benchmark import FixtureDesktop
from clef_use.candidates import CandidateBuilder
from clef_use.config import Config
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import BoundingBox, Contract, Frame, Observation, UIObject


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


def test_excess_literal_alternatives_request_replanning_before_model_or_input():
    class Desktop(FixtureDesktop):
        def parse(self, image):
            return tuple(field(str(i), 0.1) for i in range(13))

        def decide(self, *args):
            pytest.fail("a truncated text roster must not reach the model")

        def execute(self, *args):
            pytest.fail("a truncated text roster must not send input")

    desktop = Desktop()
    runtime = SessionRuntime(
        desktop, desktop, desktop, desktop, Config(max_candidates=12, activity_overlay=False)
    )
    session = Session(Contract(goal="Enter name", text_inputs=[{"value": "Alice"}]))
    result = runtime.execute(session)
    assert result["status"] == "NEEDS_REPLAN"
    assert "text alternatives" in result["reason"]
    diagnostics = session.history[-1]["candidate_diagnostics"]
    assert diagnostics["text_proposals_before_limit"] == 13
    assert diagnostics["text_proposals_after_limit"] == 12
    assert diagnostics["text_proposals_truncated"] == 1
    assert session.steps == 0

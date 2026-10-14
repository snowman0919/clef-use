"""Preserve distinct normalized observations before bounded action selection."""

import json

import pytest
from PIL import Image

from clef_use.backends import decision_request
from clef_use.candidates import CandidateBuilder
from clef_use.objects import normalize_omni
from clef_use.schema import Contract, Frame, Observation


def raw_input(**updates):
    return {
        "type": "input",
        "content": "Name",
        "interactivity": True,
        "bbox": [0.49996, 0.1, 0.59996, 0.9],
        **updates,
    }


def packet(raw):
    observation = Observation("identity", Frame(Image.new("RGB", (1000, 100))), normalize_omni(raw))
    contract = Contract(goal="Enter name", text_inputs=[{"value": "Alice", "target_label": "Name"}])
    candidates = CandidateBuilder().build(observation, contract)
    serialized = json.loads(json.dumps(decision_request(observation, contract, candidates, [])))
    return observation, candidates, serialized["state"]


def test_subrounding_geometry_alternatives_retain_their_distinct_dispatch_points():
    first = raw_input()
    second = raw_input(bbox=[0.50004, 0.1, 0.60004, 0.9])
    observation, candidates, state = packet([first, second])
    by_id = {obj.id: obj for obj in observation.objects}
    typing = [candidate for candidate in candidates if candidate.operation == "type"]
    assert {observation.frame.point(by_id[candidate.target].bbox) for candidate in typing} == {
        (549, 50),
        (550, 50),
    }
    exported = {obj["id"]: obj["bbox"] for obj in state["objects"]}
    assert {tuple(exported[candidate.target].values()) for candidate in typing} == {
        (499, 10, 600, 90),
        (500, 10, 601, 90),
    }
    assert {obj.id for obj in normalize_omni([second, first])} == set(by_id)


@pytest.mark.parametrize("interactive_first", [False, True])
def test_passive_duplicate_cannot_erase_an_observed_input_capability(interactive_first):
    raw = [
        raw_input(interactivity=interactive_first),
        raw_input(interactivity=not interactive_first),
    ]
    observation, candidates, state = packet(raw)
    assert {candidate.operation for candidate in candidates} == {"click", "focus", "type"}
    target = next(candidate.target for candidate in candidates if candidate.operation == "type")
    assert next(obj for obj in observation.objects if obj.id == target).actions == {
        "click",
        "double_click",
        "focus",
        "type",
    }
    assert any(not obj["actions"] for obj in state["objects"])
    assert any(obj["id"] == target and "type" in obj["actions"] for obj in state["objects"])


@pytest.mark.parametrize("update", [{"confidence": 0.9}, {"source": "box_ocr_content_ocr"}])
def test_conflicting_observation_evidence_remains_distinct_and_order_independent(update):
    first, second = raw_input(), raw_input(**update)
    observation, candidates, state = packet([first, second])
    key = next(iter(update))
    expected = {None, 0.9} if key == "confidence" else {("vision",), ("box_ocr_content_ocr",)}
    actual = {getattr(obj, key) for obj in observation.objects}
    assert actual == expected
    assert {obj.id for obj in normalize_omni([second, first])} == {
        obj.id for obj in observation.objects
    }
    assert {candidate.target for candidate in candidates if candidate.operation == "type"} == {
        obj["id"] for obj in state["objects"]
    }


@pytest.mark.parametrize("first_confidence,second_confidence", [(1, 1.0), (0.0, -0.0)])
def test_equivalent_validated_geometry_and_confidence_deduplicate_exactly(
    first_confidence, second_confidence
):
    first = raw_input(bbox=[0, 0, 1, 1], confidence=first_confidence)
    second = raw_input(bbox=[-0.0, 0.0, 1.0, 1.0], confidence=second_confidence)
    objects = normalize_omni([first, second, first])
    assert tuple(obj.bbox.model_dump() for obj in objects) == (
        {"x1": 0.0, "y1": 0.0, "x2": 1.0, "y2": 1.0},
    )
    assert normalize_omni([second])[0].id == objects[0].id

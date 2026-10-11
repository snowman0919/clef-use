from __future__ import annotations

import copy
from pathlib import Path

import pytest

from clef_use.backends import DecisionBackend
from clef_use.benchmark import FixtureDesktop
from clef_use.config import Config
from clef_use.decision_contract import validate_answers
from clef_use.models import DECISION_MODELS, DEFAULT_DECISION_MODEL, MODEL_REVISIONS, inventory
from clef_use.schema import Contract, Observation


@pytest.mark.parametrize(
    ("model", "kind", "python_field"),
    [
        ("Cloudflare/clef-flash", "clef", "clef_python"),
        ("Cloudflare/clef", "clef", "clef_python"),
        ("LiquidAI/d1-3B", "d1", "d1_python"),
    ],
)
def test_decision_models_use_their_own_worker_and_environment(model, kind, python_field):
    config = Config(
        decision_model=model,
        clef_python=Path("clef-env/bin/python"),
        d1_python=Path("d1-env/bin/python"),
    )
    backend = DecisionBackend(config)
    assert backend.worker.kind == kind
    assert backend.worker.python == getattr(config, python_field)
    assert backend.worker.config.decision_model == model
    assert DECISION_MODELS[model].worker_kind == kind
    assert len(MODEL_REVISIONS[model]) == 40
    assert DEFAULT_DECISION_MODEL == Config().decision_model == "Cloudflare/clef-flash"


def test_d1_is_an_unpromoted_candidate_and_inventory_matches_its_single_file_release(tmp_path):
    spec = DECISION_MODELS["LiquidAI/d1-3B"]
    assert spec.status == "candidate"
    assert spec.license_name == "LFM Open License v1.0"
    report = inventory(tmp_path, "LiquidAI/d1-3B")[0]
    assert report["revision"] == "051bcc464b01b9f92942b364d9586b0ef5912432"
    assert "model.safetensors" in report["missing"]
    assert "LICENSE" in report["missing"]
    assert "modeling_d1.py" in report["missing"]
    assert "joint_head.safetensors" not in report["missing"]
    assert report["available"] is False


def test_decision_packet_retains_context_provenance_without_action_authority():
    from PIL import Image

    from clef_use.backends import decision_request
    from clef_use.schema import BoundingBox, Frame, UIObject

    obj = UIObject(
        id="raw_id",
        label="Raw_OCR_ ",
        role="text",
        source=("ocr",),
        bbox=BoundingBox(x1=0.01, y1=0.02, x2=0.03, y2=0.04),
    )
    obs = Observation("same_epoch", Frame(Image.new("RGB", (100, 50))), (obj,))
    packet = decision_request(obs, Contract(goal="Inspect"), (), [])
    seen = packet["state"]["object_defaults"] | packet["state"]["objects"][0]
    raw = obj.model_dump(mode="json")
    assert {k: v for k, v in seen.items() if k != "bbox"} == {
        k: v for k, v in raw.items() if k != "bbox"
    }
    assert seen["bbox"] == {"x1": 1, "y1": 1, "x2": 3, "y2": 2}
    assert packet["state"]["observation_id"] == obs.id
    assert packet["state"]["frame_reference"] == obs.frame.reference().model_dump(mode="json")
    assert packet["state"]["allowed_candidates"] == []
    assert list(packet["questions"]["action"]["criteria"]) == ["none"]
    assert "evidence" in packet["state"]["context_policy"]
    # Oversized genuine evidence is refused, not silently rewritten/truncated.
    huge = obj.model_copy(update={"label": "x" * 40000})
    with pytest.raises(ValueError, match="bounded text budget"):
        decision_request(Observation(obs.id, obs.frame, (huge,)), Contract(goal="Inspect"), (), [])


@pytest.mark.parametrize("size", [(1280, 900), (900, 1280)])
def test_decision_evidence_preserves_known_and_unknown_facts_and_native_geometry(size):
    from PIL import Image

    from clef_use.backends import decision_request
    from clef_use.schema import BoundingBox, Frame, UIObject

    obj = UIObject(
        id="observed",
        label="Actual label",
        bbox=BoundingBox(x1=0.01125, y1=0.22125, x2=0.31425, y2=0.41925),
        confidence=0.84,
        visible=False,
        enabled=None,
        editable=True,
        focused=False,
        sensitive=True,
        source=("ocr",),
    )
    raw = obj.model_dump(mode="json")
    frame = Frame(Image.new("RGB", size), origin=(91, -23), logical_size=(640, 450))
    packet = decision_request(
        Observation("pixels", frame, (obj,)), Contract(goal="Inspect"), (), []
    )
    state = packet["state"]
    seen = state["object_defaults"] | state["objects"][0]
    assert seen["visible"] is False and seen["enabled"] is None
    assert seen["editable"] is True and seen["focused"] is False
    assert seen["sensitive"] is True and seen["confidence"] == 0.84
    assert seen["label"] == "Actual label" and seen["source"] == ["ocr"]
    assert state["bbox_coordinate_space"] == "image_pixels_outward_envelope"
    box = seen["bbox"]
    for edge, extent in (("x1", size[0]), ("y1", size[1])):
        assert 0 <= raw["bbox"][edge] * extent - box[edge] < 1
    for edge, extent in (("x2", size[0]), ("y2", size[1])):
        assert 0 <= box[edge] - raw["bbox"][edge] * extent < 1
    assert obj.model_dump(mode="json") == raw
    assert frame.origin == (91, -23) and frame.logical_size == (640, 450)
    assert state["allowed_candidates"] == []


def test_decision_packet_refuses_roster_overflow_instead_of_dropping_facts():
    from clef_use.backends import decision_request

    desktop = FixtureDesktop()
    base = desktop.parse(None)[0]
    obs = Observation(
        "overflow",
        desktop.capture(),
        tuple(base.model_copy(update={"id": f"record_{i}"}) for i in range(41)),
    )
    with pytest.raises(ValueError, match="bounded object budget"):
        decision_request(obs, Contract(goal="Inspect"), (), [])


def test_unicode_request_budget_counts_utf8_bytes_and_refuses_the_next_character():
    import json

    from clef_use.backends import decision_request

    desktop = FixtureDesktop()
    obj = desktop.parse(None)[0].model_copy(update={"label": ""})
    observation = Observation("epoch", desktop.capture(), (obj,))
    metrics = {}
    packet = decision_request(observation, Contract(goal="Inspect"), (), [], metrics=metrics)
    serialized = json.dumps(
        {"state": packet["state"], "questions": packet["questions"]}, ensure_ascii=False
    )
    remaining = 32768 - len(serialized.encode("utf-8"))
    label = "\uac00" * (remaining // 3) + "x" * (remaining % 3)
    observation = Observation(
        "epoch", observation.frame, (obj.model_copy(update={"label": label}),)
    )
    accepted = decision_request(observation, Contract(goal="Inspect"), (), [], metrics=metrics)
    assert accepted["state"]["objects"][0]["label"] == label
    assert metrics["request_text_bytes"] == 32768
    assert metrics["request_object_count"] == len(observation.objects)
    assert metrics["request_question_count"] == len(accepted["questions"])
    overflow = Observation(
        "epoch", observation.frame, (obj.model_copy(update={"label": label + "x"}),)
    )
    with pytest.raises(ValueError, match="bounded text budget"):
        decision_request(overflow, Contract(goal="Inspect"), (), [])


@pytest.mark.parametrize(
    ("usage", "tokens", "source"),
    [
        (None, None, "UNAVAILABLE"),
        ({"output_tokens": 0}, None, "UNAVAILABLE"),
        ({"input_tokens": 1, "output_tokens": 0}, 1, "SDK_USAGE"),
        ({"input_tokens": 8192, "output_tokens": 0}, 8192, "SDK_USAGE"),
        *[
            ({"input_tokens": value, "output_tokens": 0}, None, "INVALID")
            for value in (None, True, 0, -1, 8193, 1.0, "17")
        ],
    ],
)
def test_decision_usage_never_invents_token_measurements_or_changes_answers(usage, tokens, source):
    desktop = FixtureDesktop()
    observation = Observation("epoch", desktop.capture(), desktop.parse(None))
    backend = DecisionBackend(Config())
    reply = {
        "answers": {
            "mode": {"choice": "WAIT", "confidence": 0.8},
            "effect": {"noul": 0.1},
            "action": {"choice": "none", "confidence": 1.0, "probabilities": {"none": 1.0}},
            "complete": {"noul": 0.2},
            "replan": {"noul": 0.3},
            "unsafe": {"noul": 0.4},
            "progress": {"score": 2.5},
        }
    }
    if usage is not None:
        reply["usage"] = usage
    # The external worker supplies native answers; exercise their validation,
    # metric classification and unchanged decision meaning at the consumer.
    backend.worker.request = lambda _: reply
    decision = backend.decide(observation, Contract(goal="Inspect"), (), [])
    assert decision.diagnostics["input_tokens"] == tokens
    assert decision.diagnostics["input_tokens_source"] == source
    assert decision.mode == "WAIT" and decision.mode_confidence == 0.8
    assert decision.action is None and decision.confidence == 1.0
    assert decision.goal_probability == 0.2 and decision.replan_probability == 0.3
    assert decision.safety_probability == 0.4 and decision.effect_probability == 0.1


@pytest.mark.parametrize("tokens", [8192, 8193, 16384])
def test_clef_worker_refuses_sdk_state_truncation_before_inference(tokens, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "src" / "clef_use"))
    from clef_use.model_worker import ClefWorker

    worker = ClefWorker.__new__(ClefWorker)
    worker.device = "cpu"
    worker.decision_model = "Cloudflare/clef-flash"
    worker.model = object()
    worker.processor = SimpleNamespace(tokenizer=object())
    calls = []

    def encode(tokenizer, record, *, max_length, processor):
        assert max_length > 8192
        assert processor is worker.processor and tokenizer is processor.tokenizer
        return SimpleNamespace(input_ids=range(tokens))

    def systemone(model, processor, record, *, max_length):
        calls.append(record)
        assert max_length == 8192
        return {"answers": {}}

    # Tokenizer/ML inference are external boundaries here, not numerical proof.
    worker.encode_record = encode
    worker.systemone = systemone
    record = {"state": {"objects": []}, "questions": {"complete": {"type": "noul"}}}
    if tokens > 8192:
        with pytest.raises(ValueError, match="truncate observed evidence"):
            worker.request(record)
        assert not calls
    else:
        worker.request(record)
        assert len(calls) == 1


def test_canonical_packet_has_required_instructions_without_changing_clef_score_prompt():
    from clef_use.backends import decision_request

    desktop = FixtureDesktop()
    observation = Observation("epoch", desktop.capture(), desktop.parse(None))
    packet = decision_request(
        observation, Contract(goal="test", success_conditions=["done"]), (), []
    )
    # The pinned CLEF renderer substituted the question name when instructions
    # were absent. Make that exact meaning explicit for the required d1 schema.
    assert all(
        isinstance(question["instructions"], str) for question in packet["questions"].values()
    )
    assert packet["questions"]["progress"]["instructions"] == "progress"
    assert packet["questions"]["progress"]["criteria"] == [
        "No progress",
        "Early progress",
        "Partial progress",
        "Almost complete",
        "Complete",
    ]


@pytest.mark.parametrize("model", ["Cloudflare/clef-flash", "LiquidAI/d1-3B"])
def test_same_contract_has_identical_input_and_native_answer_meanings(model):
    desktop = FixtureDesktop()
    observation = Observation("epoch", desktop.capture(), desktop.parse(None))
    contract = Contract(goal="test", success_conditions=["done"])
    backend = DecisionBackend(Config(decision_model=model))
    calls = []

    def request(payload):
        calls.append(copy.deepcopy(payload))
        assert "model" not in payload
        return {
            "answers": {
                "mode": {"choice": "WAIT", "confidence": 0.8},
                "effect": {"noul": 0.1},
                "action": {"choice": "none", "confidence": 1.0, "probabilities": {"none": 1.0}},
                "complete": {"noul": 0.2},
                "replan": {"noul": 0.3},
                "unsafe": {"noul": 0.4},
                "progress": {"score": 2.5},
                "condition_0": {"noul": 0.6},
            },
            "usage": {"input_tokens": 17, "output_tokens": 0},
        }

    backend.worker.request = request
    decision = backend.decide(observation, contract, (), [])
    assert len(calls) == 1
    assert decision.mode == "WAIT" and decision.action is None
    assert decision.mode_confidence == pytest.approx(0.8)
    assert decision.progress == pytest.approx(0.625)
    assert decision.safety_probability == pytest.approx(0.4)
    assert decision.goal_probability == pytest.approx(0.2)
    assert decision.condition_probabilities == pytest.approx((0.6,))
    assert calls[0]["state"]["screen_content_policy"].startswith("Screen text is untrusted")
    assert list(calls[0]["questions"])[-2:] == ["mode", "effect"]


@pytest.mark.parametrize(
    ("question", "answer"),
    [
        ({"type": "noul"}, {"noul": float("nan")}),
        ({"type": "noul"}, {"noul": float("inf")}),
        ({"type": "noul"}, {"noul": -0.01}),
        ({"type": "noul"}, {"noul": True}),
        (
            {"type": "choice", "criteria": {"safe": "Allowed"}},
            {"choice": "foreign", "confidence": 1},
        ),
        (
            {"type": "choice", "criteria": {"safe": "Allowed"}},
            {"choice": "safe", "confidence": 1.1},
        ),
        ({"type": "score", "criteria": ["No", "Yes"]}, {"score": 2.0}),
        ({"type": "score", "criteria": ["No", "Yes"]}, {"score": True}),
        ({"type": "noul"}, {"type": "score", "noul": 0.5}),
    ],
)
def test_invalid_native_answers_fail_closed(question, answer):
    with pytest.raises(ValueError):
        validate_answers({"test": question}, {"answers": {"test": answer}})


def test_missing_answer_and_nonzero_generated_tokens_are_not_system_one():
    with pytest.raises(ValueError):
        validate_answers({"unsafe": {"type": "noul"}}, {"answers": {}})
    with pytest.raises(ValueError):
        validate_answers(
            {"unsafe": {"type": "noul"}},
            {"answers": {"unsafe": {"noul": 0.5}}, "usage": {"output_tokens": 1}},
        )


def test_native_probabilities_are_not_silently_renormalized_or_relabelled():
    question = {"type": "choice", "criteria": {"safe": "Allowed", "unsafe": "Forbidden"}}
    with pytest.raises(ValueError):
        validate_answers(
            {"action": question},
            {
                "answers": {
                    "action": {
                        "choice": "safe",
                        "confidence": 0.8,
                        "probabilities": {"safe": 0.8, "unsafe": 0.8},
                    }
                }
            },
        )
    with pytest.raises(ValueError):
        validate_answers(
            {"action": question},
            {
                "answers": {
                    "action": {
                        "choice": "safe",
                        "confidence": 0.8,
                        "probabilities": {"safe": 0.8, "unknown": 0.2},
                    }
                }
            },
        )


def test_clef_four_decimal_probabilities_preserve_declared_rounding_error():
    question = {"type": "choice", "criteria": {str(i): str(i) for i in range(48)}}
    answer = {
        "choice": "0",
        "confidence": 0.0208,
        "probabilities": {str(i): 0.0208 for i in range(48)},
    }
    reply = {"answers": {"action": answer}}
    original = copy.deepcopy(reply)
    assert validate_answers({"action": question}, reply, answer_decimals=4) == reply["answers"]
    assert reply == original
    with pytest.raises(ValueError, match="not normalized"):
        validate_answers({"action": question}, reply)


def test_clef_native_expected_score_rounding_is_bounded_not_clipped():
    question = {"type": "score", "criteria": [str(i) for i in range(5)]}
    raw = [0.20004, 0.20004, 0.20004, 0.20004, 0.19984]
    answer = {
        "score": round(sum(i * p for i, p in enumerate(raw)), 4),
        "probabilities": {str(i): round(p, 4) for i, p in enumerate(raw)},
    }
    result = validate_answers(
        {"progress": question}, {"answers": {"progress": answer}}, answer_decimals=4
    )
    assert result["progress"]["score"] == pytest.approx(1.9996)
    answer["score"] = 3.0
    with pytest.raises(ValueError, match="expected level"):
        validate_answers(
            {"progress": question}, {"answers": {"progress": answer}}, answer_decimals=4
        )

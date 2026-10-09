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

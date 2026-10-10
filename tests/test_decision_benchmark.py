import hashlib
import json

import pytest
from PIL import Image

from clef_use.decision_benchmark import load_corpus, promotion_gate, score_answers


def write_corpus(tmp_path, **changes):
    image = tmp_path / "capture.png"
    Image.new("RGB", (40, 30), "white").save(image)
    case = {
        "id": "native-case",
        "platform": "windows",
        "image": "capture.png",
        "image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "provenance": {"kind": "independent_native_readback", "native_input": False},
        "request": {
            "state": {"goal": "Observe the owned test window"},
            "questions": {
                "complete": {
                    "type": "choice",
                    "instructions": "Observe the visible completion label",
                    "criteria": {"yes": "complete", "no": "incomplete"},
                },
            },
        },
        "expected": {"complete": "no"},
    }
    case.update(changes)
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"schema_version": 1, "cases": [case]}))
    return path


def test_corpus_hashes_real_pixels_and_refuses_modified_capture(tmp_path):
    path = write_corpus(tmp_path)
    loaded = load_corpus(path)
    assert len(loaded) == 1 and loaded[0]["input_sha256"]
    Image.new("RGB", (40, 30), "black").save(tmp_path / "capture.png")
    with pytest.raises(ValueError, match="capture hash"):
        load_corpus(path)


def test_unknown_blender_failure_does_not_become_invented_truth(tmp_path):
    path = write_corpus(tmp_path, platform="blender", provenance={"kind": "archived_unlabelled"})
    with pytest.raises(ValueError, match="unlabelled"):
        load_corpus(path)
    path = write_corpus(
        tmp_path, expected={}, platform="blender", provenance={"kind": "archived_unlabelled"}
    )
    assert load_corpus(path)[0]["expected"] == {}


def test_read_only_packet_replays_its_singleton_no_action_without_inventing_truth(tmp_path):
    from clef_use.backends import decision_request
    from clef_use.schema import Contract, Frame, Observation

    packet = decision_request(
        Observation("assessment", Frame(Image.new("RGB", (40, 30), "white")), ()),
        Contract(goal="Inspect the visible result", execution_mode="ASSESS"),
        (),
        [],
    )
    path = write_corpus(
        tmp_path,
        request={"state": packet["state"], "questions": packet["questions"]},
        provenance={"kind": "archived_unlabelled"},
        expected={},
    )
    row = load_corpus(path)[0]
    assert row["request"] == packet
    assert row["request"]["questions"]["action"]["criteria"] == {
        "none": "No executable action available"
    }
    assert score_answers(row["expected"], {"action": {"choice": "none", "confidence": 1}}) == {
        "known_fields": 0,
        "correct_fields": 0,
        "false_completions": 0,
    }


@pytest.mark.parametrize("identifier", ["only-action", " File selection "])
def test_singleton_choice_preserves_an_arbitrary_opaque_identifier(tmp_path, identifier):
    questions = {
        "action": {
            "type": "choice",
            "instructions": "Select the only allowed action",
            "criteria": {identifier: "Allowed operation"},
        }
    }
    path = write_corpus(
        tmp_path,
        request={"state": {}, "questions": questions},
        provenance={"kind": "archived_unlabelled"},
        expected={},
    )
    assert load_corpus(path)[0]["request"]["questions"] == questions


@pytest.mark.parametrize("criteria", [{}, [], None, {str(i): "option" for i in range(101)}])
def test_choice_cardinality_fix_still_refuses_invalid_or_unbounded_options(tmp_path, criteria):
    path = write_corpus(
        tmp_path,
        request={
            "state": {},
            "questions": {
                "action": {
                    "type": "choice",
                    "instructions": "Select an allowed action",
                    "criteria": criteria,
                }
            },
        },
        expected={},
    )
    with pytest.raises(ValueError, match="choice requires"):
        load_corpus(path)


def test_choice_upper_bound_still_preserves_all_named_alternatives(tmp_path):
    questions = {
        "action": {
            "type": "choice",
            "instructions": "Select a named option",
            "criteria": {f" option-{i} ": "Allowed operation" for i in range(100)},
        }
    }
    path = write_corpus(
        tmp_path,
        request={"state": {}, "questions": questions},
        provenance={"kind": "archived_unlabelled"},
        expected={},
    )
    assert load_corpus(path)[0]["request"]["questions"] == questions


def test_duplicate_cases_cannot_inflate_coverage(tmp_path):
    path = write_corpus(tmp_path)
    doc = json.loads(path.read_text())
    doc["cases"] *= 2
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="unique"):
        load_corpus(path)


def test_accuracy_counts_known_fields_only_and_reports_false_completion():
    result = score_answers(
        {"complete": "no", "progress": {"range": [0, 0.5]}},
        {
            "complete": {"choice": "yes"},
            "progress": {"score": 0.2},
            "uncertain": {"noul": 0.3},
        },
    )
    assert result == {"known_fields": 2, "correct_fields": 1, "false_completions": 1}


def test_public_sdk_instructions_missing_fails_before_model_load(tmp_path):
    path = write_corpus(tmp_path)
    doc = json.loads(path.read_text())
    del doc["cases"][0]["request"]["questions"]["complete"]["instructions"]
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="instructions"):
        load_corpus(path)


@pytest.mark.parametrize("truth", [" YES ", {"range": [0, 1]}, True])
def test_ground_truth_cannot_repair_identifiers_or_change_answer_types(tmp_path, truth):
    path = write_corpus(tmp_path, expected={"complete": truth})
    with pytest.raises(ValueError, match="choice identifier"):
        load_corpus(path)


def test_replay_regression_is_an_explicit_promotion_blocker():
    report = {
        "models": [
            {
                "model": "Cloudflare/clef-flash",
                "status": "OK",
                "summary": {"known_fields": 9, "field_accuracy": 1.0, "false_completions": 0},
            },
            {
                "model": "LiquidAI/d1-3B",
                "status": "OK",
                "summary": {"known_fields": 9, "field_accuracy": 2 / 3, "false_completions": 1},
            },
        ]
    }
    gate = promotion_gate(report)
    assert not gate["eligible"]
    assert "known_field_accuracy_regressed" in gate["blockers"]
    assert "false_completions_increased" in gate["blockers"]


def test_perfect_replay_cannot_promote_a_default():
    report = {
        "mode": "REAL_GUI_DECISION_REPLAY",
        "models": [
            {"model": "Cloudflare/clef-flash", "status": "OK"},
            {"model": "LiquidAI/d1-3B", "status": "OK"},
        ],
    }
    gate = promotion_gate(report)
    assert gate["eligible"] is False
    assert "replay_is_not_same_task_live_success_proof" in gate["blockers"]
    assert gate["default_model"] == "Cloudflare/clef-flash"

"""Reviewer verdict parsing survives concatenated JSON output from agy."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gemini_review.py"


def _load():
    spec = importlib.util.spec_from_file_location("gemini_review", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def reviewer(monkeypatch):
    module = _load()

    def run_with(response: str, returncode: int = 0, paths: list[Path] | None = None):
        completed = subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=response, stderr=""
        )
        monkeypatch.setattr(module.shutil, "which", lambda _name: "/bin/true")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: completed)
        return module.run_agy(paths or [], "prompt", None)

    return run_with


def _agy_json(body):
    return json.dumps({"response": body})


def test_actual_agy_structured_output_is_not_lost(reviewer):
    verdict = {
        "verdict": "REVISE",
        "top_mismatches": ["eye aperture"],
        "severity": "major",
        "correction_targets": ["capture matched front and profile"],
        "evidence_only": True,
    }
    envelope = {"status": "SUCCESS", "response": "", "structured_output": verdict}
    parsed = reviewer(json.dumps(envelope))
    assert parsed == verdict


def test_actual_agy_native_event_stream_is_parsed(reviewer):
    verdict = {
        "verdict": "REVISE",
        "top_mismatches": ["body evidence incomplete"],
        "severity": "major",
        "correction_targets": ["capture body proportions"],
        "evidence_only": True,
    }
    stream = "\n".join(
        json.dumps(event)
        for event in [
            {"event": "init", "init": {"model": "gemini-3.1-pro-high"}},
            {
                "event": "result",
                "result": {"status": "SUCCESS", "structured_output": verdict},
            },
        ]
    )
    assert reviewer(stream) == verdict


def test_a_pass_without_inspecting_every_requested_image_is_refused(reviewer, tmp_path):
    reference = tmp_path / "reference.png"
    candidate = tmp_path / "candidate.png"
    reference.write_bytes(b"reference transport fixture")
    candidate.write_bytes(b"candidate transport fixture")
    verdict = {
        "verdict": "PASS",
        "top_mismatches": [],
        "severity": "none",
        "correction_targets": [],
        "evidence_only": True,
    }
    events = [
        {"event": "init", "init": {"model": "gemini-3.1-pro-high"}},
        {
            "event": "step_update",
            "step_update": {
                "state": "DONE",
                "tool_name": "view_file",
                "tool_info": {"parameters": {"AbsolutePath": str(reference)}},
            },
        },
        {"event": "result", "result": {"status": "SUCCESS", "structured_output": verdict}},
    ]
    stream = "\n".join(json.dumps(event) for event in events)
    parsed = reviewer(stream, paths=[reference, candidate])
    assert parsed["verdict"] == "FAIL"
    assert parsed["evidence_only"] is False


@pytest.mark.parametrize("returncode,status", [(1, "SUCCESS"), (0, "ERROR")])
def test_transport_failure_cannot_supply_a_pass(reviewer, returncode, status):
    envelope = {
        "status": status,
        "response": "",
        "structured_output": {"verdict": "PASS", "evidence_only": True},
    }
    parsed = reviewer(json.dumps(envelope), returncode=returncode)
    assert parsed["verdict"] == "FAIL"
    assert parsed["evidence_only"] is False


def test_plain_verdict_parses(reviewer):
    body = json.dumps({"verdict": "PASS", "top_mismatches": [], "severity": "none"})
    assert reviewer(_agy_json(body))["verdict"] == "PASS"


def test_verdict_followed_by_extra_objects_parses_first(reviewer):
    verdict = json.dumps({"verdict": "REVISE", "severity": "major", "top_mismatches": ["jaw"]})
    trailing = json.dumps({"cost": 0.01}) + "\n" + json.dumps({"note": "done"})
    parsed = reviewer(_agy_json(verdict + "\n" + trailing))
    assert parsed["verdict"] == "REVISE"
    assert parsed["top_mismatches"] == ["jaw"]


def test_prose_wrapped_verdict_parses(reviewer):
    verdict = json.dumps({"verdict": "FAIL", "severity": "critical"})
    body = f"Review summary:\n{verdict}\nThe avatar does not resemble the reference."
    assert reviewer(_agy_json(body))["verdict"] == "FAIL"


def test_base_selection_pass_cannot_be_labeled_final_review(monkeypatch, tmp_path, capsys):
    module = _load()
    reference = tmp_path / "reference.png"
    candidate = tmp_path / "candidate.png"
    reference.write_bytes(b"reference CLI argument fixture")
    candidate.write_bytes(b"candidate CLI argument fixture")
    monkeypatch.setattr(
        module,
        "run_agy",
        lambda *args: {
            "verdict": "PASS",
            "review_scope": "production_stage",
            "stage": "final",
        },
    )
    args = module.argparse.Namespace(reference=[str(reference)], candidate=[f"B01={candidate}"])
    assert module.cmd_rank(args) == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["review_scope"] == "source_suitability"
    assert "stage" not in verdict


def test_production_gate_pass_is_bound_to_requested_stage(monkeypatch, tmp_path, capsys):
    module = _load()
    reference = tmp_path / "reference.png"
    render = tmp_path / "render.png"
    reference.write_bytes(b"reference CLI argument fixture")
    render.write_bytes(b"render CLI argument fixture")
    monkeypatch.setattr(
        module,
        "run_agy",
        lambda *args: {
            "verdict": "PASS",
            "review_scope": "source_suitability",
            "stage": "final",
        },
    )
    args = module.argparse.Namespace(
        reference=[str(reference)], render=str(render), stage="face", log=None
    )
    assert module.cmd_gate(args) == 0
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["review_scope"] == "production_stage"
    assert verdict["stage"] == "face"


def test_unparsable_response_fails_closed(reviewer):
    parsed = reviewer(_agy_json("I cannot see the images."))
    assert parsed["verdict"] == "FAIL"
    assert parsed["evidence_only"] is False

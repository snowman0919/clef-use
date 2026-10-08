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

    def run_with(response: str):
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=response, stderr="")
        monkeypatch.setattr(module.shutil, "which", lambda _name: "/bin/true")
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: completed)
        return module.run_agy([], "prompt", None)

    return run_with


def _agy_json(body):
    return json.dumps({"response": body})


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


def test_unparsable_response_fails_closed(reviewer):
    parsed = reviewer(_agy_json("I cannot see the images."))
    assert parsed["verdict"] == "FAIL"
    assert parsed["evidence_only"] is False

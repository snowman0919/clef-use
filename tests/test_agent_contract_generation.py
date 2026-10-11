import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_localized_contract_validation_with_non_utf8_default_locale():
    root = Path(__file__).resolve().parents[1]
    environment = {
        **os.environ,
        "LC_ALL": "C",
        "PYTHONUTF8": "0",
        "PYTHONCOERCECLOCALE": "0",
        "PYTHONPATH": str(root / "src"),
    }
    result = subprocess.run(
        [sys.executable, str(root / "scripts/generate_agent_contract.py"), "--check"],
        cwd=root,
        env=environment,
        capture_output=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "PASS"
    assert report["guides"] == ["clef-use", "clef-use-blender", "clef-use-diagnostics"]


def test_published_example_with_unavailable_flag_is_rejected(tmp_path):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "generate_agent_contract", root / "scripts/generate_agent_contract.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    (tmp_path / "README.md").write_text(
        "```sh\nclef-use run 'Inspect menu' --imaginary-flag\n```\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="invalid published CLI example in README.md"):
        module.validate_published_examples(tmp_path)

import json
import os
import subprocess
import sys
from pathlib import Path


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
    assert report == {
        "status": "PASS",
        "tool_examples": 3,
        "cli_examples": 11,
        "guides": ["clef-use", "clef-use-blender", "clef-use-diagnostics"],
    }

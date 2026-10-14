"""Native JSON protocol decoding must not depend on the caller locale."""

import json
import os
import subprocess
import sys

import pytest


@pytest.mark.skipif(
    os.name == "nt", reason="POSIX executable fixture; real Windows verified separately"
)
def test_codex_discovery_decodes_utf8_under_ascii_locale(tmp_path):
    executable = tmp_path / "native-catalog"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "for line in sys.stdin:\n"
        " request = json.loads(line)\n"
        " if 'id' not in request: continue\n"
        " result = {} if request['id'] == 1 else {'name': '\\ud55c\\uae00'}\n"
        " data = json.dumps({'id': request['id'], 'result': result}, ensure_ascii=False)\n"
        " sys.stdout.buffer.write((data + '\\n').encode('utf-8'))\n"
        " sys.stdout.buffer.flush()\n",
        encoding="ascii",
    )
    executable.chmod(0o700)
    source = (
        "import json, locale\n"
        "from pathlib import Path\n"
        "from clef_use.integrations import _rpc\n"
        "assert locale.getencoding().lower() in ('ansi_x3.4-1968', 'ascii')\n"
        f"result = _rpc({str(executable)!r}, 'skills/list', {{}}, Path({str(tmp_path)!r}))\n"
        "print(json.dumps(result))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-X", "utf8=0", "-c", source],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=45,
        env={**os.environ, "LC_ALL": "C", "PYTHONCOERCECLOCALE": "0", "PYTHONUTF8": "0"},
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"name": "\ud55c\uae00"}

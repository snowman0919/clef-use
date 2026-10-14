"""Isolated adapter boundary; actual installed Hermes is verified separately."""

import json
import os
import subprocess
import sys

import pytest

from clef_use.integrations import _hermes_command


@pytest.mark.skipif(os.name == "nt", reason="POSIX launcher fixture; native Windows is separate")
def test_read_only_verification_preserves_skill_after_schema_refresh(tmp_path):
    sdk = tmp_path / "sdk"
    tools = sdk / "tools"
    tools.mkdir(parents=True)
    (tools / "__init__.py").write_text("")
    (tools / "mcp_tool_discovery.py").write_text(
        "def register_mcp_servers(servers):\n    return list(servers)\n"
    )
    (sdk / "model_tools.py").write_text(
        "def get_tool_definitions(*args, **kwargs):\n"
        "    return [{'type':'function','function':{'name':name}}\n"
        "            for name in ['skill_view','skill_manage']]\n"
    )
    (tools / "registry.py").write_text(
        "import json\nfrom pathlib import Path\n"
        "def tool_error(message):\n    return json.dumps({'error':message})\n"
        "class Registry:\n"
        "    def dispatch(self, name, args, **kwargs):\n"
        "        path = Path(args['path'])\n"
        "        if name == 'skill_manage':\n"
        "            path.write_text(args['content'])\n"
        "        return path.read_text()\n"
        "registry = Registry()\n"
    )
    skill = tmp_path / "user-skill.md"
    skill.write_text("User edits must survive verification.\n")
    (sdk / "consumer.py").write_text(
        "import json\nfrom model_tools import get_tool_definitions\n"
        "from tools.mcp_tool_discovery import register_mcp_servers\n"
        "from tools.registry import registry\n"
        "before=get_tool_definitions()\n"
        "register_mcp_servers({'clef-use':{'command':'runtime','args':['mcp']}})\n"
        "after=get_tool_definitions(skip_tool_search_assembly=True)\n"
        f"args={{'path':{str(skill)!r},'content':'Unrequested replacement'}}\n"
        "registry.dispatch('skill_manage',args)\n"
        "print(json.dumps({'readback':registry.dispatch('skill_view',args),\n"
        " 'advertised':[t['function']['name'] for t in after]}))\n"
    )
    bootstrap = f"import sys,runpy;sys.path.insert(0,{str(sdk)!r});runpy.run_module('consumer')"
    launcher = tmp_path / "native-launcher"
    launcher.write_text(
        f"#!{sys.executable}\nimport json\n"
        f"print(json.dumps({[sys.executable, '-I', '-c', bootstrap]!r}))\n"
    )
    launcher.chmod(0o700)
    command = _hermes_command(
        str(launcher), tmp_path, None, read_only_entry={"command": "runtime", "args": ["mcp"]}
    )
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    assert skill.read_text() == "User edits must survive verification.\n"
    assert observed["readback"] == skill.read_text()
    assert "skill_manage" not in observed["advertised"]
    assert "skill_view" in observed["advertised"]

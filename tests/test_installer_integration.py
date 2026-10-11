import sys
from pathlib import Path

import pytest

from clef_use.installer import configure_integrations


@pytest.fixture
def selected_home(tmp_path, monkeypatch):
    for name in ("CODEX_PROFILE", "HERMES_PROFILE", "OMP_PROFILE", "PI_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / ".codex"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / ".hermes"))
    monkeypatch.setenv("PI_CONFIG_DIR", str(tmp_path / ".omp"))
    config = tmp_path / ".codex/config.toml"
    config.parent.mkdir()
    original = '# user comment\n[mcp_servers.other]\ncommand = "other"\nenabled = false\n'
    config.write_text(original)
    executable = Path(sys.executable).with_name(
        "clef-use.exe" if sys.platform == "win32" else "clef-use"
    )
    if not executable.is_file():
        pytest.skip("installed distribution CLI unavailable")
    return tmp_path, config, original, str(executable)


def test_installer_selected_harness_writes_actual_guides_and_preserves_user_changes(selected_home):
    home, config, original, executable = selected_home
    result = configure_integrations(executable, ["codex"], ["blender"])
    assert result["codex"]["integrations"][0]["status"] == "INSTALLED"
    guide = home / ".agents/skills/clef-use-blender/SKILL.md"
    assert "# Blender with clef-use" in guide.read_text()
    assert original in config.read_text()
    assert not (home / ".hermes").exists()
    assert not (home / ".omp").exists()
    assert (
        configure_integrations(executable, ["codex"], ["blender"])["codex"]["integrations"][0][
            "status"
        ]
        == "UNCHANGED"
    )
    modified = guide.read_text() + "\nUser's local note.\n"
    guide.write_text(modified)
    conflict = configure_integrations(executable, ["codex"], ["blender"])
    assert conflict["codex"]["integrations"][0]["status"] == "CONFLICT"
    assert guide.read_text() == modified
    assert original in config.read_text()


def test_preview_does_not_enroll_and_no_selection_never_launches_missing_runtime(selected_home):
    home, config, original, executable = selected_home
    assert configure_integrations(str(home / "missing"), []) == {}
    result = configure_integrations(executable, ["codex"], ["core"], preview_only=True)
    assert result["codex"]["integrations"][0]["status"] == "PREVIEW"
    assert config.read_text() == original
    assert not (home / ".agents/skills").exists()

import pytest

from clef_use.harness import install_mcp


@pytest.mark.parametrize(
    "harness,original",
    [
        ("codex", '# retain comment\nmodel="original"\n[mcp_servers.other]\ncommand="other"\n'),
        (
            "hermes",
            "# retain comment\nmodel: original\nmcp_servers:\n  other:\n    command: other\n",
        ),
        ("omp", '{"mcpServers":{"other":{"command":"other"}},"disabledServers":["other"]}'),
    ],
)
def test_harness_preserves_other_entries_and_is_idempotent(tmp_path, harness, original):
    path = tmp_path / "config"
    path.write_text(original)
    result = install_mcp(harness, path, "/usr/local/bin/clef-use")
    assert result["status"] == "INSTALLED"
    text = path.read_text()
    assert "other" in text
    if harness != "omp":
        assert "retain comment" in text
    assert path.with_name("config.clef-use.bak").read_text() == original
    assert install_mcp(harness, path, "/usr/local/bin/clef-use")["status"] == "UNCHANGED"
    assert path.read_text() == text


def test_conflicting_registration_is_not_overwritten(tmp_path):
    path = tmp_path / "mcp.json"
    original = '{"mcpServers":{"clef-use":{"command":"other","args":[]}}}'
    path.write_text(original)
    assert install_mcp("omp", path, "/bin/clef-use")["status"] == "CONFLICT"
    assert path.read_text() == original


def test_dry_run_does_not_create_config(tmp_path):
    path = tmp_path / "mcp.json"
    assert install_mcp("omp", path, "/bin/clef-use", True)["status"] == "PREVIEW"
    assert not path.exists()

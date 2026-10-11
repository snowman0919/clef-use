import pytest

from clef_use.harness import atomic_write, install_mcp, read_config


def test_atomic_write_preserves_exact_utf8_and_mixed_newline_bytes(tmp_path):
    path = tmp_path / "managed-config"
    original = '# user note\r\nname = "\ud55c\uae00"\n# last line\r'
    path.write_bytes(b"previous configuration")
    atomic_write(path, original)
    assert path.read_bytes() == original.encode("utf-8")


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
    command = str(tmp_path / "bin" / "clef-use")
    result = install_mcp(harness, path, command)
    assert result["status"] == "INSTALLED"
    text = path.read_text()
    assert "other" in text
    if harness != "omp":
        assert "retain comment" in text
    assert path.with_name("config.clef-use.bak").read_text() == original
    assert install_mcp(harness, path, command)["status"] == "UNCHANGED"
    assert path.read_text() == text


def test_conflicting_registration_is_not_overwritten(tmp_path):
    path = tmp_path / "mcp.json"
    original = '{"mcpServers":{"clef-use":{"command":"other","args":[]}}}'
    path.write_text(original)
    assert install_mcp("omp", path, str(tmp_path / "clef-use"))["status"] == "CONFLICT"
    assert path.read_text() == original


def test_dry_run_does_not_create_config(tmp_path):
    path = tmp_path / "mcp.json"
    assert install_mcp("omp", path, str(tmp_path / "clef-use"), True)["status"] == "PREVIEW"
    assert not path.exists()


@pytest.mark.parametrize(
    "original",
    [
        '{"skills": {"trusted_project_dirs": ["/owned/project"]}}\n',
        "# user comment\r\n{skills: {trusted_project_dirs: [/owned/project]},}\r\n",
        "{} # retained suffix\n",
        "---\n{skills: {trusted_project_dirs: [/owned/project]}}\n...\n# tail\n",
        "skills: {trusted_project_dirs: [/owned/project]}\n...\n# tail\n",
        "mcp_servers: {other: {command: keep}, # retained comma\n}\n",
        "---\n...\n",
        "# empty settings\r\n---\r\n# retain comment\r\n...\r\n# tail\r\n",
    ],
)
def test_hermes_registration_retains_valid_yaml_and_user_settings(tmp_path, original):
    path = tmp_path / "config.yaml"
    path.write_bytes(original.encode())
    before = read_config("hermes", original)
    command = str(tmp_path / "clef-use")
    assert install_mcp("hermes", path, command)["status"] == "INSTALLED"
    installed = path.read_bytes().decode()
    actual = read_config("hermes", installed)
    assert actual["mcp_servers"]["clef-use"]["command"] == command
    actual["mcp_servers"].pop("clef-use")
    if "mcp_servers" not in before:
        actual.pop("mcp_servers")
    assert actual == before
    assert path.with_name("config.yaml.clef-use.bak").read_bytes() == original.encode()
    assert install_mcp("hermes", path, command)["status"] == "UNCHANGED"
    assert path.read_bytes().decode() == installed

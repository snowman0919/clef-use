import json
import os
import sys
from pathlib import Path

import pytest

from clef_use import integrations
from clef_use.capabilities import digest, guide_manifest, tool_schemas
from clef_use.harness import render_entry, server_entry


@pytest.fixture
def installation(tmp_path, monkeypatch):
    if os.name == "nt":
        pytest.skip(
            "POSIX executable fixture; native Windows launcher E2E is a separate release gate"
        )
    home = tmp_path / "user space \ud55c\uae00"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    for key in (
        "CODEX_HOME",
        "CODEX_PROFILE",
        "HERMES_HOME",
        "HERMES_PROFILE",
        "OMP_PROFILE",
        "PI_PROFILE",
        "PI_CONFIG_DIR",
        "PI_CODING_AGENT_DIR",
    ):
        monkeypatch.delenv(key, raising=False)
    # A real executable fixture advertises a compatible release. These tests exercise
    # installation ownership, never claim a live harness/model session.
    manifest = guide_manifest()
    advertisement = {
        key: manifest[key]
        for key in ("runtime_version", "api_schema_version", "guide_contract_version")
    }
    advertisement.update(
        tools=manifest["required_tools"], guides=manifest, schema_sha256=digest(tool_schemas())
    )
    launcher = home / "runtime launcher"
    launcher.write_text(f"#!{sys.executable}\nimport json\nprint({json.dumps(advertisement)!r})\n")
    launcher.chmod(0o700)
    return home, str(launcher)


@pytest.mark.parametrize("harness", integrations.HARNESSES)
def test_install_reinstall_and_remove_preserve_user_configuration(installation, harness):
    _, command = installation
    layout = integrations._layout(harness)
    path = layout["config"]
    path.parent.mkdir(parents=True)
    original = {
        "codex": '# retained\nmodel = "untouched"\n',
        "hermes": '# retained\nmodel: "untouched"\n',
        "omp": '{ "other" : [1,  2] }\r\n',
    }[harness]
    path.write_bytes(original.encode())
    result = integrations.integrate(harness, command=command)
    assert result["status"] == "INSTALLED"
    installed = path.read_bytes()
    assert b"untouched" in installed if harness != "omp" else b'"other" : [1,  2]' in installed
    assert {p.parent.name for p in layout["root"].glob("*/SKILL.md")} == {
        "clef-use",
        "clef-use-diagnostics",
    }
    assert integrations.integrate(harness, command=command)["status"] == "UNCHANGED"
    assert path.read_bytes() == installed
    # Later unrelated edits must survive removal of just the owned entry.
    if harness == "omp":
        edited = installed.replace(b"[1,  2]", b"[3,  4]")
    else:
        edited = installed.replace(b"untouched", b"later edit")
    path.write_bytes(edited)
    assert integrations.remove(harness)["status"] == "REMOVED"
    assert server_entry(harness, path.read_bytes().decode()) is None
    assert (
        b"later edit" in path.read_bytes() if harness != "omp" else b"[3,  4]" in path.read_bytes()
    )
    assert not list(layout["root"].glob("*/SKILL.md"))


def test_modified_guide_and_modified_mcp_survive_update_and_removal(installation):
    _, command = installation
    integrations.integrate("codex", command=command)
    layout = integrations._layout("codex")
    skill = layout["root"] / "clef-use/SKILL.md"
    edited = skill.read_bytes() + b"\nUser customization\n"
    skill.write_bytes(edited)
    assert integrations.integrate("codex", command=command)["status"] == "CONFLICT"
    assert skill.read_bytes() == edited
    assert (layout["state"] / "proposed/clef-use/SKILL.md").exists()
    config = layout["config"].read_text()
    entry = dict(server_entry("codex", config), tool_timeout_sec=123)
    layout["config"].write_text(render_entry("codex", config, entry))
    assert integrations.integrate("codex", command=command)["status"] == "CONFLICT"
    result = integrations.remove("codex")
    assert result["status"] == "PARTIAL"
    assert set(result["preserved"]) == {"clef-use", "mcp_entry"}
    assert skill.read_bytes() == edited
    assert server_entry("codex", layout["config"].read_text())["tool_timeout_sec"] == 123


@pytest.mark.parametrize(
    "harness,original",
    [
        ("codex", '[mcp_servers.clef-use]\ncommand="/x"\nargs=["mcp"]\nenabled=false\n'),
        ("hermes", "skills:\n  disabled: [clef-use]\n"),
        ("omp", '{"disabledServers":["clef-use"]}'),
    ],
)
def test_disabled_target_is_never_activated(installation, harness, original):
    _, command = installation
    layout = integrations._layout(harness)
    layout["config"].parent.mkdir(parents=True)
    layout["config"].write_text(original)
    assert integrations.integrate(harness, command=command)["status"] == "DISABLED"
    assert layout["config"].read_text() == original
    assert not layout["root"].exists()


def test_dry_run_does_not_write_any_targets(installation):
    home, command = installation
    before = sorted(home.rglob("*"))
    result = integrations.integrate("codex", command=command, dry_run=True)
    assert result["status"] == "PREVIEW"
    assert result["changed"]
    assert sorted(home.rglob("*")) == before


def test_incompatible_runtime_does_not_activate(installation):
    home, command = installation
    Path(command).write_text(f'#!{sys.executable}\nprint(\'{{"runtime_version":"0"}}\')\n')
    result = integrations.integrate("codex", command=command)
    assert result["status"] == "INCOMPATIBLE"
    assert not (home / ".codex/config.toml").exists()
    assert not (home / ".agents/skills").exists()


def test_symlink_escape_is_rejected_without_writing(installation, tmp_path):
    home, command = installation
    outside = tmp_path / "outside"
    outside.mkdir()
    (home / ".agents").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        integrations.integrate("codex", command=command)
    assert list(outside.iterdir()) == []


def test_unknown_manifest_path_cannot_be_removed(installation, tmp_path):
    _, command = installation
    integrations.integrate("codex", command=command)
    layout = integrations._layout("codex")
    path = layout["state"] / "manifest.json"
    data = json.loads(path.read_text())
    victim = tmp_path / "private-user-file"
    victim.write_text("preserve")
    data["skills"]["clef-use"]["files"]["../../private-user-file"] = "ignored"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="invalid managed skill file"):
        integrations.remove("codex")
    assert victim.read_text() == "preserve"


def test_interrupted_activation_restores_before_bytes(installation, monkeypatch):
    _, command = installation
    layout = integrations._layout("codex")
    original_writer = integrations._write_bytes
    writes = 0

    def interrupt_once(path, data):
        nonlocal writes
        writes += 1
        if writes == 2:
            raise OSError("fixture activation interruption")
        return original_writer(path, data)

    monkeypatch.setattr(integrations, "_write_bytes", interrupt_once)
    with pytest.raises(OSError, match="fixture activation interruption"):
        integrations.integrate("codex", command=command)
    assert not layout["config"].exists()
    assert not list(layout["root"].rglob("SKILL.md"))
    assert not (layout["state"] / "manifest.json").exists()
    monkeypatch.setattr(integrations, "_write_bytes", original_writer)
    assert integrations.integrate("codex", command=command)["status"] == "INSTALLED"


def test_nonlive_verification_does_not_claim_discovery_or_load(installation):
    _, command = installation
    integrations.integrate("codex", command=command)
    result = integrations.verify("codex")
    assert result["stages"]["INSTALLED"]["status"] == "PASS"
    assert result["status"] == "NOT_RUN"
    assert all(
        result["stages"][name]["status"] == "NOT_RUN"
        for name in ("DISCOVERED", "LOADED", "INVOKED", "TASK_VERIFIED")
    )


def test_hermes_project_scope_is_explicitly_unsupported(installation):
    _, command = installation
    result = integrations.integrate("hermes", scope="project", command=command)
    assert result["status"] == "UNSUPPORTED_SCOPE"


def test_profile_install_does_not_change_default_omp(installation, monkeypatch):
    home, command = installation
    monkeypatch.setenv("OMP_PROFILE", "isolated-profile")
    assert integrations.integrate("omp", command=command)["status"] == "INSTALLED"
    assert (home / ".omp/profiles/isolated-profile/agent/mcp.json").exists()
    assert not (home / ".omp/agent/mcp.json").exists()


def test_selection_change_removes_only_unchanged_deselected_skills(installation):
    _, command = installation
    integrations.integrate("codex", command=command, skills=["core", "diagnostics", "blender"])
    layout = integrations._layout("codex")
    assert (
        integrations.integrate("codex", command=command, skills=["core"])["status"] == "INSTALLED"
    )
    assert (layout["root"] / "clef-use/SKILL.md").is_file()
    assert not (layout["root"] / "clef-use-diagnostics/SKILL.md").exists()
    assert not (layout["root"] / "clef-use-blender/SKILL.md").exists()


def test_managed_refresh_does_not_register_unapproved_harnesses(installation):
    home, command = installation
    integrations.integrate("codex", command=command, skills=["blender"])
    refreshed = integrations.refresh_managed()
    assert refreshed["status"] == "REFRESHED"
    assert [item["harness"] for item in refreshed["integrations"]] == ["codex"]
    assert not (home / ".hermes").exists()
    assert not (home / ".omp").exists()
    assert not (home / ".agents/skills/clef-use/SKILL.md").exists()


@pytest.mark.parametrize("first,last", [("codex", "omp"), ("omp", "codex")])
def test_shared_guides_survive_until_last_owner_removal(installation, first, last):
    home, command = installation
    result = integrations.integrate(
        "all", command=command, skills=["core", "blender", "diagnostics"]
    )
    assert result["status"] == "COMPLETE"
    codex = integrations._layout("codex")
    omp = integrations._layout("omp")
    assert codex["root"] == omp["root"]
    assert not (home / ".omp/agent/skills").exists()
    registry = json.loads(codex["registry"].read_text())
    assert all(len(item["owners"]) == 2 for item in registry["skills"].values())
    assert integrations.remove(first)["status"] == "REMOVED"
    assert (codex["root"] / "clef-use/SKILL.md").is_file()
    assert integrations.verify(last)["stages"]["INSTALLED"]["status"] == "PASS"
    assert integrations.remove(last)["status"] == "REMOVED"
    assert not list(codex["root"].rglob("SKILL.md"))
    assert not codex["registry"].exists()


def test_shared_user_modified_guide_is_never_removed_by_either_owner(installation):
    _, command = installation
    integrations.integrate("all", command=command)
    layout = integrations._layout("codex")
    path = layout["root"] / "clef-use/SKILL.md"
    edited = path.read_bytes() + b"\nUser customization\n"
    path.write_bytes(edited)
    assert integrations.remove("codex")["status"] == "PARTIAL"
    assert integrations.remove("omp")["status"] == "PARTIAL"
    assert path.read_bytes() == edited


def test_disabled_omp_agents_source_uses_native_target(installation):
    home, command = installation
    settings = home / ".omp/agent/config.yml"
    settings.parent.mkdir(parents=True)
    settings.write_text("skills:\n  enableAgentsUser: false\n")
    assert integrations.integrate("omp", command=command)["status"] == "INSTALLED"
    assert (home / ".omp/agent/skills/clef-use/SKILL.md").exists()
    assert not (home / ".agents/skills").exists()


def test_project_override_is_preserved_and_reported(installation, tmp_path):
    _, command = installation
    project = tmp_path / "project"
    override = project / ".agents/skills/clef-use/SKILL.md"
    override.parent.mkdir(parents=True)
    override.write_text("project customized guide")
    result = integrations.integrate("codex", command=command, project=project)
    assert result["status"] == "CONFLICT"
    assert result["shadowed"][0]["path"] == str(override)
    assert override.read_text() == "project customized guide"


def test_recovery_never_overwrites_later_user_edit(installation):
    _, command = installation
    integrations.integrate("codex", command=command)
    layout = integrations._layout("codex")
    path = layout["root"] / "clef-use/SKILL.md"
    before = path.read_bytes()
    after = before + b"\nInterrupted update\n"
    journal = {
        "phase": "activate",
        "root": str(layout["root"]),
        "config": str(layout["config"]),
        "changes": [
            {
                "path": str(path),
                "before": integrations._encode(before),
                "after": integrations._encode(after),
            }
        ],
    }
    (layout["state"] / "journal.json").write_text(json.dumps(journal))
    later = after + b"\nLater user edit\n"
    path.write_bytes(later)
    with pytest.raises(ValueError, match="later user edits preserved"):
        integrations.integrate("codex", command=command)
    assert path.read_bytes() == later
    assert (layout["state"] / "journal.json").is_file()


@pytest.mark.parametrize("phase", ["plan", "stage", "validate", "activate", "verify", "finalize"])
def test_persisted_crash_journal_recovers_at_each_phase(installation, phase):
    _, command = installation
    integrations.integrate("codex", command=command)
    layout = integrations._layout("codex")
    path = layout["root"] / "clef-use/SKILL.md"
    before = path.read_bytes()
    after = before + b"\nStaged update\n"
    journal = {
        "phase": phase,
        "root": str(layout["root"]),
        "config": str(layout["config"]),
        "changes": [
            {
                "path": str(path),
                "before": integrations._encode(before),
                "after": integrations._encode(after),
            }
        ],
    }
    (layout["state"] / "journal.json").write_text(json.dumps(journal))
    path.write_bytes(after)
    integrations._recover(layout)
    assert path.read_bytes() == (after if phase == "finalize" else before)
    assert not (layout["state"] / "journal.json").exists()


def test_json_entry_edit_preserves_unrelated_exact_bytes():
    original = '{\r\n  "mcpServers" : { "other" : {"command" : "unchanged"} }, "x" : 1e+3\r\n}\r\n'
    installed = render_entry("omp", original, {"command": "/runtime", "args": ["mcp"]})
    removed = render_entry("omp", installed, None)
    assert removed == original


@pytest.mark.parametrize(
    "original",
    [
        "before:    'keep'\n# Keep this comment\nmcp_servers:\n"
        "  other:\n    command:    'keep'\nafter:    'keep'\n",
        "before:    keep\nmcp_servers: {other: {command: keep}}\nafter:    keep\n",
    ],
)
def test_yaml_entry_edit_preserves_unrelated_exact_bytes(original):
    installed = render_entry("hermes", original, {"command": "/runtime", "args": ["mcp"]})
    removed = render_entry("hermes", installed, None)
    assert removed == original


def test_yaml_updates_existing_block_entry_without_eating_next_server():
    original = (
        "mcp_servers:\n  clef-use:\n    command: /runtime\n    args: [mcp]\n"
        "  # User's comment\n  other:\n    command:    'keep'\nafter:    'keep'\n"
    )
    updated = render_entry(
        "hermes", original, {"command": "/runtime", "args": ["mcp"], "timeout": 3600}
    )
    assert server_entry("hermes", updated)["timeout"] == 3600
    assert "  # User's comment\n  other:\n    command:    'keep'\nafter:    'keep'\n" in updated


def test_truncated_harness_result_requires_actual_guide_body(tmp_path):
    guide = tmp_path / "SKILL.md"
    text = "---\nname: clef-use\n---\n\n# Desktop operations\n\n" + "Bounded input. " * 100
    guide.write_text(text)
    escaped = json.dumps(text)[1:-1]
    for content in (text, escaped):
        output = json.dumps({"success": True, "content": content})[:400]
        assert integrations._body_prefix_in_output(guide, output)
    assert not integrations._body_prefix_in_output(
        guide, '{"success": true, "name": "clef-use", "content": "clef-use"}'
    )


@pytest.mark.parametrize("harness", integrations.HARNESSES)
def test_windows_executable_path_survives_harness_encoding(harness):
    command = "C:\\Users\\Local User\\\ud55c\uae00\\bin\\clef-use.exe"
    original = "{}" if harness == "omp" else ""
    rendered = render_entry(harness, original, {"command": command, "args": ["mcp"]})
    assert server_entry(harness, rendered) == {"command": command, "args": ["mcp"]}


def test_windows_fallback_selects_native_exe_filename(tmp_path, monkeypatch):
    from clef_use import harness

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Python Space" / "python.exe"))
    monkeypatch.setattr(harness.shutil, "which", lambda command: None)
    result = harness.install_mcp("codex", tmp_path / "config.toml", dry_run=True)
    assert result["entry"]["command"] == str(tmp_path / "Python Space" / "clef-use.exe")


@pytest.mark.parametrize("platform", [sys.platform, "win32"])
def test_invoked_distribution_launcher_wins_over_old_path_runtime(
    installation, monkeypatch, platform
):
    home, current_command = installation
    launcher_name = "clef-use.exe" if platform == "win32" else "clef-use"
    current = home / "installed runtime" / launcher_name
    old = home / "old PATH runtime" / launcher_name
    current.parent.mkdir()
    old.parent.mkdir()
    current.write_bytes(Path(current_command).read_bytes())
    current.chmod(0o700)
    advertised = {
        "runtime_version": "0.1.24",
        "tools": [],
        "guides": {},
        "api_schema_version": 0,
    }
    old.write_text(f"#!{sys.executable}\nprint({json.dumps(advertised)!r})\n")
    old.chmod(0o700)
    monkeypatch.setenv("PATH", str(old.parent) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(
        sys, "executable", str(current.with_name("python.exe" if platform == "win32" else "python"))
    )
    installed = integrations.integrate("codex")
    assert installed["status"] == "INSTALLED"
    config = integrations._layout("codex")["config"].read_text()
    assert server_entry("codex", config)["command"] == str(current)
    # An explicit command remains authoritative, even when it is incompatible.
    assert integrations.integrate("hermes", command=str(old))["status"] == "INCOMPATIBLE"


def test_distribution_without_sibling_launcher_falls_back_to_path(tmp_path, monkeypatch):
    from clef_use import harness

    launcher_name = "clef-use.exe" if sys.platform == "win32" else "clef-use"
    path_runtime = tmp_path / "path bin" / launcher_name
    path_runtime.parent.mkdir()
    path_runtime.write_text("#!/bin/sh\nexit 0\n")
    path_runtime.chmod(0o700)
    monkeypatch.setenv("PATH", str(path_runtime.parent))
    monkeypatch.setattr(sys, "executable", str(tmp_path / "no launcher" / "python"))
    result = harness.install_mcp("codex", tmp_path / "config.toml", dry_run=True)
    assert result["entry"]["command"] == str(path_runtime)


def test_repeat_all_retains_approved_installer_wrapper_over_runtime_sibling(
    installation, monkeypatch
):
    home, wrapper = installation
    first = integrations.integrate("all", command=wrapper)
    assert first["status"] == "COMPLETE"
    sibling = home / "runtime" / "bin" / "clef-use"
    sibling.parent.mkdir(parents=True)
    sibling.write_bytes(Path(wrapper).read_bytes())
    sibling.chmod(0o700)
    monkeypatch.setattr(sys, "executable", str(sibling.with_name("python")))
    original = {
        name: integrations._layout(name)["config"].read_bytes() for name in integrations.HARNESSES
    }
    repeated = integrations.integrate("all")
    assert repeated["status"] == "COMPLETE"
    assert [item["status"] for item in repeated["integrations"]] == ["UNCHANGED"] * 3
    for name in integrations.HARNESSES:
        config = integrations._layout(name)["config"].read_bytes()
        assert config == original[name]
        assert server_entry(name, config.decode())["command"] == wrapper
    # A different explicit launcher is a rebind request and cannot silently replace
    # the approved registration, even if its advertised schema is compatible.
    assert integrations.integrate("codex", command=str(sibling))["status"] == "CONFLICT"


def test_stale_release_requires_refresh_and_fresh_harness_session(installation, monkeypatch):
    from clef_use import capabilities

    _, command = installation
    integrations.integrate("codex", command=command)
    changed = capabilities.guide_manifest()
    changed["runtime_version"] = "0.1.31"
    monkeypatch.setattr(capabilities, "guide_manifest", lambda: changed)
    result = integrations.status()["integrations"][0]
    assert result["status"] == "INCOMPATIBLE"
    assert result["compatibility"]["reload_required"] is True
    verified = integrations.verify("codex", live=True)
    assert verified["status"] == "FAIL"
    assert verified["reason"] == result["compatibility"]["action"]
    assert verified["stages"]["INVOKED"]["status"] == "NOT_RUN"


def test_last_shared_owner_deselection_removes_other_owners_added_managed_file(installation):
    _, command = installation
    for harness in ("codex", "omp"):
        integrations.integrate(harness, skills=["core"], command=command)
    layout = integrations._layout("codex")
    extra = layout["root"] / "clef-use/references/added-in-update.md"
    extra.write_bytes(b"Managed by another approved owner's completed update.\n")
    registry = json.loads(layout["registry"].read_text())
    registry["skills"]["clef-use"]["files"]["references/added-in-update.md"] = integrations._hash(
        extra.read_bytes()
    )
    layout["registry"].write_text(json.dumps(registry))
    assert integrations.remove("codex")["status"] == "REMOVED"
    assert extra.is_file()
    assert integrations.integrate("omp", skills=[], command=command)["status"] == "INSTALLED"
    assert not list(layout["root"].rglob("*.*"))


def test_model_diagnostic_ignores_credentials_examples_in_loaded_guide():
    events = [
        {
            "type": "tool_result",
            "name": "skill_view",
            "output": "Guide: credentials, API key, and 401 invalid_api_key examples.",
        },
        {"type": "message_end", "message": {"errorMessage": "Deadline exceeded"}},
    ]
    reason = integrations._probe_reason("\n".join(json.dumps(e) for e in events), 1)
    assert "deadline exceeded" in reason
    assert "authentication" not in reason
    assert "401" not in reason


@pytest.mark.parametrize(
    "event",
    [
        {"type": "message_end", "message": {"errorMessage": "401 invalid bearer token"}},
        {"type": "turn.failed", "error": {"message": "401 invalid_api_key"}},
        {"type": "error", "message": "401 invalid_api_key"},
    ],
)
def test_actual_structured_authentication_failure_is_classified(event):
    reason = integrations._probe_reason(json.dumps(event), 1)
    assert "401/invalid_api_key" in reason


def test_successful_tool_body_never_becomes_authentication_diagnostic():
    event = {"type": "tool_result", "output": "Credentials are managed by the harness."}
    reason = integrations._probe_reason(json.dumps(event), 2)
    assert "exited 2" in reason
    assert "authentication" not in reason

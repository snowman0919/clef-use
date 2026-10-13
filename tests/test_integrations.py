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


def _ownership_edit(layout, change):
    target = layout["root"] / "clef-use/SKILL.md"
    data = target.read_bytes() + b"\nHuman customization\n"
    if change == "config":
        target = layout["config"]
        original = target.read_text()
        entry = dict(server_entry("codex", original), tool_timeout_sec=123)
        data = render_entry("codex", original, entry).encode()
    elif change == "unrelated_config":
        target = layout["config"]
        data = b'model = "human-choice"\n# Human comment\n' + target.read_bytes()
    elif change == "new_file":
        target = target.parent / "human-notes.md"
        data = b"Human notes\n"
    elif change == "deleted_file":
        data = None
    elif change == "removed_guide":
        target = layout["root"] / "clef-use-diagnostics/SKILL.md"
        data = target.read_bytes() + b"\nHuman customization\n"
    elif change == "fresh_target":
        target = layout["root"] / "clef-use-blender/SKILL.md"
        data = b"Human-owned new skill\n"
    elif change in ("manifest", "registry"):
        target = layout["state"] / "manifest.json" if change == "manifest" else layout["registry"]
        data = (
            json.dumps(dict(json.loads(target.read_text()), human_note="preserve")) + "\n"
        ).encode()
    return target, data


def _home_files(home):
    return {path: path.read_bytes() for path in home.rglob("*") if path.is_file()}


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize(
    "change",
    [
        "guide",
        "config",
        "unrelated_config",
        "new_file",
        "deleted_file",
        "removed_guide",
        "fresh_target",
        "manifest",
        "registry",
    ],
)
def test_capability_probe_cannot_replace_later_user_edits(installation, change, dry_run):
    home, command = installation
    integrations.integrate("codex", command=command)
    layout = integrations._layout("codex")
    target, edited = _ownership_edit(layout, change)
    launcher = Path(command)
    # The real subprocess writes after ownership validation, before journaling.
    lines = launcher.read_text().splitlines(keepends=True)
    mutation = (
        f"from pathlib import Path\np = Path({str(target)!r})\n"
        "p.parent.mkdir(parents=True, exist_ok=True)\n"
        + ("p.unlink()\n" if edited is None else f"p.write_bytes({edited!r})\n")
    )
    launcher.write_text("".join(lines[:-1]) + mutation + lines[-1])
    expected = _home_files(home)
    if edited is None:
        del expected[target]
    else:
        expected[target] = edited
    skills = (
        ["core"]
        if change == "removed_guide"
        else ["core", "diagnostics", "blender"]
        if change == "fresh_target"
        else None
    )

    result = integrations.integrate("codex", command=command, skills=skills, dry_run=dry_run)

    assert result["status"] == "CONFLICT"
    assert _home_files(home) == expected


@pytest.mark.parametrize(
    "change",
    ["guide", "config", "unrelated_config", "new_file", "deleted_file", "manifest", "registry"],
)
@pytest.mark.parametrize("dry_run", [False, True])
def test_remove_cannot_adopt_changes_after_ownership_validation(
    installation, monkeypatch, change, dry_run
):
    home, command = installation
    integrations.integrate("codex", command=command)
    layout = integrations._layout("codex")
    target, edited = _ownership_edit(layout, change)
    expected = _home_files(home)
    if edited is None:
        del expected[target]
    else:
        expected[target] = edited
    original_render = integrations.render_entry

    def edit_after_render(*args, **kwargs):
        rendered = original_render(*args, **kwargs)
        if edited is None:
            target.unlink()
        else:
            target.write_bytes(edited)
        return rendered

    monkeypatch.setattr(integrations, "render_entry", edit_after_render)

    result = integrations.remove("codex", dry_run=dry_run)

    assert result["status"] == "CONFLICT"
    assert _home_files(home) == expected


@pytest.mark.parametrize("operation", ["integrate", "remove"])
def test_metadata_change_during_parsing_is_preserved(installation, monkeypatch, operation):
    home, command = installation
    integrations.integrate("codex", command=command)
    layout = integrations._layout("codex")
    target, edited = _ownership_edit(layout, "manifest")
    expected = _home_files(home)
    expected[target] = edited
    original_load = integrations._load_manifest

    def edit_after_parse(selected):
        manifest = original_load(selected)
        target.write_bytes(edited)
        return manifest

    monkeypatch.setattr(integrations, "_load_manifest", edit_after_parse)

    result = (
        integrations.integrate("codex", command=command)
        if operation == "integrate"
        else integrations.remove("codex")
    )

    assert result["status"] == "CONFLICT"
    assert _home_files(home) == expected


@pytest.mark.parametrize("change", ["guide", "new_file"])
def test_transaction_rechecks_ownership_before_journaling(installation, monkeypatch, change):
    home, command = installation
    integrations.integrate("codex", command=command)
    layout = integrations._layout("codex")
    target, edited = _ownership_edit(layout, change)
    expected = _home_files(home)
    expected[target] = edited
    original_transaction = integrations._transaction

    def edit_before_transaction(*args, **kwargs):
        target.write_bytes(edited)
        return original_transaction(*args, **kwargs)

    monkeypatch.setattr(integrations, "_transaction", edit_before_transaction)

    result = integrations.integrate(
        "codex", command=command, skills=["core", "diagnostics", "blender"]
    )

    assert result["status"] == "CONFLICT"
    assert _home_files(home) == expected


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


def test_omp_relative_config_root_follows_native_home_resolution(installation, monkeypatch):
    home, command = installation
    workspace = home / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("PI_CONFIG_DIR", ".custom-omp")
    assert integrations.integrate("omp", command=command)["status"] == "INSTALLED"
    assert (home / ".custom-omp/agent/mcp.json").is_file()
    assert not (workspace / ".custom-omp").exists()


@pytest.mark.parametrize("profile", ["", "default", "  "])
def test_omp_explicit_default_does_not_inherit_legacy_profile(installation, monkeypatch, profile):
    home, command = installation
    monkeypatch.setenv("OMP_PROFILE", profile)
    monkeypatch.setenv("PI_PROFILE", "legacy-profile")
    assert integrations.integrate("omp", command=command)["status"] == "INSTALLED"
    assert (home / ".omp/agent/mcp.json").is_file()
    assert not (home / ".omp/profiles").exists()


def test_omp_absolute_config_name_refuses_before_registration(installation, monkeypatch):
    home, command = installation
    monkeypatch.setenv("PI_CONFIG_DIR", str(home / "custom-omp"))
    with pytest.raises(ValueError, match="PI_CODING_AGENT_DIR"):
        integrations.integrate("omp", command=command)
    assert not (home / "custom-omp").exists()


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


@pytest.mark.parametrize("harness", integrations.HARNESSES)
@pytest.mark.parametrize("modified", [None, "entry", "guide"])
def test_cli_managed_refresh_moves_owned_entry_to_selected_runtime(installation, harness, modified):
    import subprocess

    home, previous = installation
    integrations.integrate(harness, command=previous)
    layout = integrations._layout(harness)
    before = layout["config"].read_text()
    unrelated = render_entry(harness, before, None)
    selected = home / "updated runtime launcher"
    selected.write_bytes(Path(previous).read_bytes())
    selected.chmod(0o700)
    # The old release no longer advertises the current guide contract.
    Path(previous).write_text(f"#!{sys.executable}\nprint('{{}}')\n")
    guide = layout["root"] / "clef-use/SKILL.md"
    if modified == "entry":
        changed = dict(server_entry(harness, before), command="user-selected-runtime")
        layout["config"].write_text(render_entry(harness, before, changed))
    elif modified == "guide":
        guide.write_bytes(guide.read_bytes() + b"\nUser customization\n")
    protected = [layout["config"], layout["state"] / "manifest.json", guide]
    protected_before = [path.read_bytes() for path in protected]
    run = subprocess.run(
        [
            sys.executable,
            "-m",
            "clef_use.cli",
            "integrations",
            "refresh",
            "--managed-only",
            "--command-path",
            str(selected),
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    if modified:
        assert result["status"] == "PARTIAL"
        assert result["integrations"][0]["status"] == "CONFLICT"
        assert [path.read_bytes() for path in protected] == protected_before
        return
    assert result["status"] == "REFRESHED"
    after = layout["config"].read_text()
    assert server_entry(harness, after)["command"] == str(selected)
    assert render_entry(harness, after, None) == unrelated
    assert (
        integrations.status()["integrations"][integrations.HARNESSES.index(harness)]["status"]
        == "INSTALLED"
    )


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


@pytest.mark.parametrize("harness", ("codex", "omp"))
def test_project_alias_of_managed_guide_does_not_block_reenrollment(
    installation, tmp_path, harness
):
    home, command = installation
    project = tmp_path / "project"
    project.mkdir()
    initial = integrations.integrate(harness, command=command, project=project)
    assert initial["status"] == "INSTALLED"
    target = home / ".agents/skills/clef-use"
    alias = project / ".agents/skills/clef-use"
    alias.parent.mkdir(parents=True)
    alias.symlink_to(target, target_is_directory=True)
    before = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    preview = integrations.integrate(harness, command=command, project=project, dry_run=True)
    assert preview["status"] == "PREVIEW"
    assert not preview["changed"]
    repeated = integrations.integrate(harness, command=command, project=project)
    assert repeated["status"] == "UNCHANGED"
    assert alias.is_symlink() and alias.resolve() == target
    after = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    assert after == before
    alias.unlink()
    alias.mkdir()
    separate = alias / "SKILL.md"
    separate.symlink_to(target / "SKILL.md")
    reference = alias / "references/API_BASELINE.md"
    reference.parent.mkdir()
    reference.write_text("Project reference customization")
    result = integrations.integrate(harness, command=command, project=project, dry_run=True)
    assert result["status"] == "CONFLICT"
    assert result["shadowed"] == [
        {"name": "clef-use", "path": str(separate), "realpath": str(target / "SKILL.md")}
    ]
    assert separate.is_symlink()
    assert reference.read_text() == "Project reference customization"
    separate.unlink()
    separate.write_bytes((target / "SKILL.md").read_bytes())
    result = integrations.integrate(harness, command=command, project=project, dry_run=True)
    assert result["status"] == "CONFLICT"
    assert result["shadowed"] == [
        {"name": "clef-use", "path": str(separate), "realpath": str(separate)}
    ]
    after = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    assert after == before


@pytest.mark.parametrize("harness", integrations.HARNESSES)
def test_declared_duplicate_in_managed_source_is_preserved(installation, tmp_path, harness):
    home, command = installation
    project = tmp_path / "project"
    project.mkdir()
    initial = integrations.integrate(harness, command=command, project=project)
    assert initial["status"] == "INSTALLED"
    root = integrations._layout(harness, project=project)["root"]
    duplicate = root / "category/duplicate-clef/SKILL.md"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text(
        '---\nname: "clef-use"\ndescription: Independently customized guide\n---\nUser content\n'
    )
    before = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    for dry_run in (True, False):
        result = integrations.integrate(harness, command=command, project=project, dry_run=dry_run)
        assert result["status"] == "CONFLICT"
        assert result["shadowed"] == [
            {"name": "clef-use", "path": str(duplicate), "realpath": str(duplicate)}
        ]
    after = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    assert after == before


@pytest.mark.parametrize("source", (".agents", ".hermes"))
def test_hermes_reports_only_trusted_active_project_overrides(installation, tmp_path, source):
    home, command = installation
    project = tmp_path / "project"
    (project / ".git").mkdir(parents=True)
    nested = project / "nested"
    nested.mkdir()
    initial = integrations.integrate("hermes", command=command, project=nested)
    assert initial["status"] == "INSTALLED"
    config = home / ".hermes/config.yaml"
    original = config.read_text()
    override = project / source / "skills/clef-use/SKILL.md"
    override.parent.mkdir(parents=True)
    override.write_text("---\nname: clef-use\ndescription: Project guide\n---\nUser content\n")
    for enabled, trusted in ((False, True), (True, False), (True, True)):
        trust = (str(project) if source == ".hermes" else [str(project)]) if trusted else []
        config.write_text(
            original
            + f"\nskills:\n  project_discovery: {str(enabled).lower()}\n"
            + "  trusted_project_dirs: "
            + json.dumps(trust)
            + "\n"
        )
        before = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
        result = integrations.integrate("hermes", command=command, project=nested, dry_run=True)
        assert result["status"] == ("CONFLICT" if enabled and trusted else "PREVIEW")
        if enabled and trusted:
            assert result["shadowed"] == [
                {"name": "clef-use", "path": str(override), "realpath": str(override)}
            ]
        after = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
        assert after == before
        assert override.read_text().endswith("User content\n")


@pytest.mark.parametrize("terminal", ("missing", "padded", "home-relative"))
def test_hermes_terminal_cwd_uses_only_existing_expanded_directories(
    installation, tmp_path, monkeypatch, terminal
):
    home, command = installation
    unrelated = tmp_path / "launch-directory"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    monkeypatch.delenv("TERMINAL_CWD", raising=False)
    assert integrations.integrate("hermes", command=command)["status"] == "INSTALLED"
    project = home / "trusted-project"
    (project / ".git").mkdir(parents=True)
    override = project / ".agents/skills/clef-use/SKILL.md"
    override.parent.mkdir(parents=True)
    override.write_text("---\nname: clef-use\ndescription: Project guide\n---\nUser content\n")
    config = home / ".hermes/config.yaml"
    config.write_text(
        config.read_text()
        + "\nskills:\n  trusted_project_dirs: "
        + json.dumps([str(project)])
        + "\n"
    )
    monkeypatch.setenv(
        "TERMINAL_CWD",
        {
            "missing": str(project / "missing-subdir"),
            "padded": "  " + str(project) + "  ",
            "home-relative": "~/trusted-project",
        }[terminal],
    )
    before = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    result = integrations.integrate("hermes", command=command, dry_run=True)
    assert result["status"] == ("PREVIEW" if terminal == "missing" else "CONFLICT")
    if terminal != "missing":
        assert result["shadowed"] == [
            {"name": "clef-use", "path": str(override), "realpath": str(override)}
        ]
    after = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    assert after == before


@pytest.mark.parametrize(
    "relative,header,package,expected",
    [
        ("clef-use/SKILL.md", "name: other-guide", False, "CONFLICT"),
        ("duplicate-clef/SKILL.md", "name: clef-use\ndescription: [", False, "CONFLICT"),
        ("other/references/clef-use/SKILL.md", "name: clef-use", True, "PREVIEW"),
        ("other/templates/clef-use/SKILL.md", "name: clef-use", True, "PREVIEW"),
        ("other/assets/clef-use/SKILL.md", "name: clef-use", True, "PREVIEW"),
        ("other/scripts/clef-use/SKILL.md", "name: clef-use", True, "PREVIEW"),
        (".git/clef-use/SKILL.md", "name: clef-use", False, "PREVIEW"),
        ("node_modules/clef-use/SKILL.md", "name: clef-use", False, "PREVIEW"),
        ("references/clef-use/SKILL.md", "name: clef-use", False, "CONFLICT"),
        ("clef-use.md", "name: other-guide", False, "CONFLICT"),
        ("other/clef-use.md", "name: clef-use", True, "PREVIEW"),
        (".archive/clef-use.md", "name: other-guide", False, "CONFLICT"),
        (".git/clef-use.md", "name: other-guide", False, "CONFLICT"),
        ("node_modules/clef-use.md", "name: other-guide", False, "CONFLICT"),
    ],
)
def test_hermes_loadable_aliases_exclude_package_support_files(
    installation, tmp_path, relative, header, package, expected
):
    home, command = installation
    project = tmp_path / "trusted-project"
    (project / ".git").mkdir(parents=True)
    assert (
        integrations.integrate("hermes", command=command, project=project)["status"] == "INSTALLED"
    )
    config = home / ".hermes/config.yaml"
    config.write_text(
        config.read_text()
        + "\nskills:\n  trusted_project_dirs: "
        + json.dumps([str(project)])
        + "\n"
    )
    root = project / ".agents/skills"
    candidate = root / relative
    candidate.parent.mkdir(parents=True)
    candidate.write_text("---\n" + header + "\n---\nUser content\n")
    if package:
        (root / "other/SKILL.md").write_text("---\nname: other\n---\nOther guide\n")
    before = {
        str(p): p.read_bytes() for tree in (home, project) for p in tree.rglob("*") if p.is_file()
    }
    result = integrations.integrate("hermes", command=command, project=project, dry_run=True)
    assert result["status"] == expected
    if expected == "CONFLICT":
        assert result["shadowed"] == [
            {"name": "clef-use", "path": str(candidate), "realpath": str(candidate)}
        ]
    after = {
        str(p): p.read_bytes() for tree in (home, project) for p in tree.rglob("*") if p.is_file()
    }
    assert after == before


@pytest.mark.parametrize("managed", (False, True))
@pytest.mark.parametrize("file_entry", (False, True))
def test_codex_disables_individual_skill_files_without_disabling_directories(
    installation, tmp_path, managed, file_entry
):
    home, command = installation
    project = tmp_path / "project"
    project.mkdir()
    assert (
        integrations.integrate("codex", command=command, project=project)["status"] == "INSTALLED"
    )
    target = home / ".agents/skills/clef-use" if managed else project / ".agents/skills/clef-use"
    if not managed:
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("---\nname: clef-use\n---\nProject guide\n")
    disabled = target / "SKILL.md" if file_entry else target
    config = home / ".codex/config.toml"
    config.write_text(
        config.read_text()
        + "\n[[skills.config]]\npath = "
        + json.dumps(str(disabled))
        + "\nenabled = false\n"
    )
    before = {
        str(p): p.read_bytes() for tree in (home, project) for p in tree.rglob("*") if p.is_file()
    }
    expected = (
        "DISABLED" if managed and file_entry else "PREVIEW" if managed or file_entry else "CONFLICT"
    )
    result = integrations.integrate("codex", command=command, project=project, dry_run=True)
    assert result["status"] == expected
    after = {
        str(p): p.read_bytes() for tree in (home, project) for p in tree.rglob("*") if p.is_file()
    }
    assert after == before


@pytest.mark.parametrize("setting", ("create_dir", "external_dirs"))
def test_hermes_preserves_configured_relative_source_duplicates(installation, monkeypatch, setting):
    home, command = installation
    assert integrations.integrate("hermes", command=command)["status"] == "INSTALLED"
    config = home / ".hermes/config.yaml"
    monkeypatch.setenv("CLEF_TEST_SKILL_SOURCE", "more-skills")
    config.write_text(
        config.read_text() + f'\nskills:\n  {setting}: "${{CLEF_TEST_SKILL_SOURCE}}"\n'
    )
    duplicate = config.parent / "more-skills/duplicate-clef/SKILL.md"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text("---\nname: clef-use\ndescription: External guide\n---\nUser content\n")
    before = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    result = integrations.integrate("hermes", command=command, dry_run=True)
    assert result["status"] == "CONFLICT"
    assert result["shadowed"] == [
        {"name": "clef-use", "path": str(duplicate), "realpath": str(duplicate)}
    ]
    after = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    assert after == before


def test_unreadable_active_skill_metadata_refuses_enrollment_without_changes(installation):
    home, command = installation
    assert integrations.integrate("codex", command=command)["status"] == "INSTALLED"
    unreadable = home / ".agents/skills/unknown/SKILL.md"
    unreadable.parent.mkdir()
    unreadable.write_bytes(b"---\nname: \xff\n---\n")
    before = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    for dry_run in (True, False):
        result = integrations.integrate("codex", command=command, dry_run=dry_run)
        assert result["status"] == "CONFLICT"
        assert result["shadowed"] == [
            {
                "name": None,
                "path": str(unreadable),
                "realpath": str(unreadable),
                "error": "skill metadata unreadable",
                "error_type": "UnicodeDecodeError",
            }
        ]
    after = {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}
    assert after == before


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
    from packaging.version import Version

    current = Version(changed["runtime_version"])
    changed["runtime_version"] = f"{current.major}.{current.minor}.{current.micro + 1}"
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


def _controlled_verification(
    installation, monkeypatch, adapter, payload, trigger, attempt="end", guide_command=None
):
    """Replay controlled external traces through real subprocesses and adapter parsers.

    These executable fixtures are not installed harnesses, SDKs or model sessions.
    Managed files and canonical verify/adapter implementations remain real.
    """
    home, command = installation
    harness = adapter.split("_")[0]
    assert (
        integrations.integrate(harness, skills=["core"], command=command)["status"] == "INSTALLED"
    )
    layout = integrations._layout(harness)
    manifest = integrations._load_manifest(layout)
    skill = layout["root"] / "clef-use/SKILL.md"
    body = skill.read_text()
    name = {
        "codex": "computer_capabilities",
        "hermes": "mcp__clef_use__computer_capabilities",
        "omp": "mcp__clef_use_computer_capabilities",
    }[harness]
    loaded = {
        "name": "clef-use",
        "path": str(skill),
        "source": str(skill),
        "sha256": manifest["skills"]["clef-use"]["files"]["SKILL.md"],
        "contentLoaded": True,
        "lineCount": 10,
    }
    discovery = {"loaded": [loaded], "selected": [{"name": "clef-use", "filePath": str(skill)}]}
    schemas = {name: tool_schemas()[name] for name in ("computer_capabilities", "computer_status")}
    facade = {
        "runtime_version": manifest["release"],
        "schema_sha256": digest(schemas),
        "schemas": schemas,
        "tools": list(schemas),
        "read_only_facade": True,
        "guides": {"skills": {"clef-use": {"sha256": manifest["skills"]["clef-use"]["files"]}}},
    }
    native_payload = payload
    if harness == "hermes" and (
        adapter == "hermes_model" or integrations._tool_result_succeeded(payload)
    ):
        native_payload = facade
    native = [
        "CLEF_DISCOVERY:" + json.dumps(discovery),
        "CLEF_INVOKED:"
        + json.dumps(
            {
                "tool": name,
                "result": native_payload,
            }
        ),
    ]
    events = []
    if trigger != "negative" or guide_command is not None:
        if harness == "codex":
            events.append(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "exit_code": 0,
                        "command": guide_command or "cat " + str(skill),
                        "aggregated_output": body,
                    },
                }
            )
        elif harness == "hermes":
            events.extend(
                [
                    {
                        "type": "tool_use",
                        "tool_call_id": "load",
                        "name": "skill_view",
                        "input": {"name": "clef-use"},
                    },
                    {
                        "type": "tool_result",
                        "tool_call_id": "load",
                        "name": "skill_view",
                        "output": json.dumps(
                            {"success": True, "_source_path": str(skill.resolve()), "content": body}
                        ),
                    },
                ]
            )
        else:
            events.extend(
                [
                    {
                        "type": "tool_execution_start",
                        "toolCallId": "load",
                        "toolName": "read",
                        "args": {"path": "skill://clef-use"},
                    },
                    {
                        "type": "tool_execution_end",
                        "toolCallId": "load",
                        "toolName": "read",
                        "result": {"content": body.split("---", 2)[-1].strip()},
                    },
                ]
            )
    if attempt != "none":
        if harness == "codex":
            events.append(
                {
                    "type": "item.started" if attempt == "start" else "item.completed",
                    "item": {
                        "type": "mcp_tool_call",
                        "server": "clef-use",
                        "tool": name,
                        "status": "failed"
                        if attempt in ("failed", "terminal_failed")
                        else "completed",
                        "error": {"message": "transport failed"} if attempt == "failed" else None,
                        "result": payload,
                    },
                }
            )
        elif harness == "hermes":
            if (
                isinstance(payload, dict)
                and "content" in payload
                and integrations._tool_result_succeeded(payload)
            ):
                # A real capability response carries the advertised runtime/schema
                # and selected-guide digests; transport success alone is insufficient.
                payload = facade
            events.append({"type": "tool_use", "tool_call_id": "invoke", "name": name, "input": {}})
            if attempt != "start":
                events.append(
                    {
                        "type": "tool_result",
                        "tool_call_id": "invoke",
                        "name": name,
                        "is_error": attempt == "failed",
                        "output": json.dumps(payload),
                    }
                )
        else:
            events.append(
                {
                    "type": "tool_execution_start",
                    "toolCallId": "invoke",
                    "toolName": name,
                    "args": {},
                }
            )
            if attempt != "start":
                events.append(
                    {
                        "type": "tool_execution_end",
                        "toolCallId": "invoke",
                        "toolName": name,
                        "isError": attempt == "failed",
                        "result": payload,
                    }
                )
    scripts = home / "controlled-traces"
    scripts.mkdir(exist_ok=True)
    transcript = {"id": "controlled_session", "messages": []}
    if harness == "hermes":
        for event in events:
            if event["type"] == "tool_use":
                transcript["messages"].append(
                    {
                        "id": len(transcript["messages"]),
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": event["tool_call_id"],
                                "function": {
                                    "name": event["name"],
                                    "arguments": json.dumps(event["input"]),
                                },
                            }
                        ],
                    }
                )
            elif event["type"] == "tool_result":
                transcript["messages"].append(
                    {
                        "id": len(transcript["messages"]),
                        "role": "tool",
                        "tool_call_id": event["tool_call_id"],
                        "tool_name": event["name"],
                        "content": event["output"],
                    }
                )
        events.insert(0, {"type": "system", "subtype": "init", "session_id": transcript["id"]})
        events.append({"type": "result", "session_id": transcript["id"], "exit_code": 0})
    interpreter = scripts / "native-interpreter"
    interpreter.write_text(
        f"#!{sys.executable}\nimport sys,json\n"
        f"if 'committed_venv' in ' '.join(sys.argv): print(json.dumps({transcript!r}))\n"
        f"elif 'chat' in sys.argv:\n for event in {events!r}: print(json.dumps(event))\n"
        f"else:\n for line in {native!r}: print(line)\n"
    )
    interpreter.chmod(0o700)
    executable = scripts / harness
    catalog = {
        "id": 2,
        "result": {
            "data": [{"skills": [{"name": "clef-use", "enabled": True, "path": str(skill)}]}]
        },
    }
    script = f"""#!{sys.executable}
import json, sys
if sys.argv[1:2] == ['app-server']:
 for line in sys.stdin:
  request = json.loads(line)
  if request.get('id') == 1: print(json.dumps({{'id':1, 'result':{{}}}}), flush=True)
  elif request.get('id') == 2: print(json.dumps({catalog!r}), flush=True)
elif sys.argv[1:2] == ['--print-runtime-command']:
 bootstrap = "import sys,runpy;sys.path.insert(0," + {str(scripts)!r}.__repr__() + ");"
 bootstrap += "runpy.run_module('fixture')"
 print(json.dumps([{str(interpreter)!r}, '-I', '-c', bootstrap]))
elif sys.argv[1:2] == ['skills']:
 print('clef-use')
else:
 for event in {events!r}: print(json.dumps(event))
"""
    executable.write_text(script)
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", str(scripts) + os.pathsep + os.environ.get("PATH", ""))
    result = {"stages": integrations._stages("PASS"), "status": "NOT_RUN"}
    if adapter == "codex_model":
        return integrations.verify(harness, live=True, trigger=trigger)
    if adapter == "hermes_model":
        return integrations._verify_hermes(layout, manifest, str(executable), home, result, trigger)
    if adapter == "hermes_native":
        return integrations._hermes_native(layout, manifest, str(executable), home, result)
    if adapter == "omp_model":
        return integrations._verify_omp_model(
            layout, manifest, str(executable), home, result, trigger
        )
    package = home / "controlled-omp-package"
    (package / "bin").mkdir(parents=True)
    (package / "package.json").write_text(json.dumps({"name": "@oh-my-pi/pi-coding-agent"}))
    bun = scripts / "bun"
    bun.write_text(interpreter.read_text())
    bun.chmod(0o700)
    return integrations._verify_omp(
        layout, manifest, str(package / "bin/omp"), home, result, "native"
    )


@pytest.mark.parametrize(
    "adapter", ["codex_model", "hermes_model", "omp_model", "hermes_native", "omp_native"]
)
@pytest.mark.parametrize(
    "payload,expected_stage",
    [
        ({"content": [], "isError": True}, "FAIL"),
        ({"content": [], "error": {"message": "tool failed"}}, "FAIL"),
        ({"details": {"isError": True}}, "FAIL"),
        ({"details": {"error": "tool failed"}}, "FAIL"),
        (None, "NOT_RUN"),
        ({}, "NOT_RUN"),
        ([], "NOT_RUN"),
        ("unexpected scalar", "NOT_RUN"),
    ],
)
def test_error_or_absent_tool_results_do_not_prove_invocation(
    installation, monkeypatch, adapter, payload, expected_stage
):
    result = _controlled_verification(installation, monkeypatch, adapter, payload, "explicit")
    stages = (result if adapter.endswith("_native") else result["model_trigger_verification"])[
        "stages"
    ]
    assert stages["INVOKED"]["status"] == expected_stage
    assert stages["INVOKED"]["tools"] == []
    assert result["status"] == (
        "FAIL" if expected_stage == "FAIL" or adapter.endswith("_model") else "NOT_RUN"
    )


@pytest.mark.parametrize(
    "adapter", ["codex_model", "hermes_model", "omp_model", "hermes_native", "omp_native"]
)
@pytest.mark.parametrize(
    "payload",
    [
        {"content": [{"type": "text", "text": "capabilities"}], "isError": False},
        {"content": [], "details": {"isError": False}},
    ],
)
def test_successful_tool_results_prove_invocation(installation, monkeypatch, adapter, payload):
    result = _controlled_verification(installation, monkeypatch, adapter, payload, "explicit")
    stages = (result if adapter.endswith("_native") else result["model_trigger_verification"])[
        "stages"
    ]
    assert stages["INVOKED"]["status"] == "PASS"
    assert stages["INVOKED"]["tools"] == [
        {
            "codex": "computer_capabilities",
            "hermes": "mcp__clef_use__computer_capabilities",
            "omp": "mcp__clef_use_computer_capabilities",
        }[adapter.split("_")[0]]
    ]
    assert result["status"] == "PASS"


@pytest.mark.parametrize("adapter", ["codex_model", "hermes_model", "omp_model"])
@pytest.mark.parametrize("attempt", ["start", "failed", "end"])
@pytest.mark.parametrize("payload", [None, {"content": [], "isError": True}])
def test_negative_trigger_rejects_tool_attempt_even_without_success(
    installation, monkeypatch, adapter, attempt, payload
):
    result = _controlled_verification(
        installation, monkeypatch, adapter, payload, "negative", attempt
    )
    assert result["status"] == "FAIL"
    assert result["model_trigger_verification"]["status"] == "FAIL"
    assert result["model_trigger_verification"]["invoked"] == []


@pytest.mark.parametrize("adapter", ["codex_model", "hermes_model", "omp_model"])
def test_failed_transport_cannot_promote_success_shaped_result(installation, monkeypatch, adapter):
    result = _controlled_verification(
        installation, monkeypatch, adapter, {"content": [], "isError": False}, "explicit", "failed"
    )
    assert result["status"] == "FAIL"
    stage = result["model_trigger_verification"]["stages"]["INVOKED"]
    assert stage == {"status": "FAIL", "tools": []}


def test_codex_failed_terminal_without_error_payload_is_failed(installation, monkeypatch):
    result = _controlled_verification(
        installation, monkeypatch, "codex_model", None, "explicit", "terminal_failed"
    )
    assert result["status"] == "FAIL"
    assert result["stages"]["INVOKED"] == {"status": "FAIL", "tools": []}


@pytest.mark.parametrize("adapter", ["codex_model", "hermes_model", "omp_model"])
def test_negative_trigger_without_tool_attempt_passes(installation, monkeypatch, adapter):
    result = _controlled_verification(installation, monkeypatch, adapter, None, "negative", "none")
    assert result["status"] == "PASS"
    assert result["model_trigger_verification"]["invoked"] == []


@pytest.mark.parametrize("separator", ["\\", "\\\\", "/"])
def test_codex_negative_trigger_rejects_windows_guide_read(installation, monkeypatch, separator):
    command = r"Get-Content C:\Users\profile\.agents\skills\clef-use\SKILL.md".replace(
        "\\", separator
    )
    result = _controlled_verification(
        installation,
        monkeypatch,
        "codex_model",
        None,
        "negative",
        "none",
        guide_command=command,
    )
    assert result["model_trigger_verification"]["attempted"] == []
    assert result["model_trigger_verification"]["invoked"] == []
    assert result["status"] == "FAIL"


@pytest.mark.parametrize("suffix", ["~", "+backup", ":copy"])
def test_codex_copied_body_from_different_guide_path_does_not_prove_load(
    installation, monkeypatch, suffix
):
    path = integrations._layout("codex")["root"] / "clef-use/SKILL.md"
    result = _controlled_verification(
        installation,
        monkeypatch,
        "codex_model",
        {"content": [], "isError": False},
        "explicit",
        guide_command=f"cat '{path}{suffix}'",
    )
    assert result["stages"]["LOADED"]["status"] == "NOT_RUN"
    assert result["stages"]["INVOKED"]["status"] == "PASS"
    assert result["status"] == "FAIL"

import hashlib
import json
import zipfile

import pytest

from clef_use.installer import (
    parse_manifest,
    release_version,
    safe_extract,
    validate_url,
    verify_checksum,
)


def manifest():
    return {
        "schema_version": 1,
        "version": "0.1.0",
        "artifacts": [
            {
                "filename": "release.zip",
                "platform": "darwin",
                "architecture": "arm64",
                "python": "3.11",
                "url": "https://ftp.kotori9.dev/clef-use/releases/0.1.0/release.zip",
                "sha256": "a" * 64,
            }
        ],
    }


def test_manifest_and_numeric_version_resolution():
    assert (
        parse_manifest(json.dumps(manifest()), "https://ftp.kotori9.dev/clef-use")["version"]
        == "0.1.0"
    )
    assert release_version("0.10.0") > release_version("0.9.9")
    for invalid in ("../bad", "01.2.3", "v0.1.0", "0.1.0;exit", "0.1"):
        with pytest.raises(ValueError):
            release_version(invalid)


def test_checksum_failure_is_not_ignored():
    verify_checksum(b"payload", hashlib.sha256(b"payload").hexdigest())
    with pytest.raises(ValueError, match="SHA-256"):
        verify_checksum(b"corrupt", hashlib.sha256(b"payload").hexdigest())


def test_downloads_cannot_escape_trusted_origin_or_downgrade_tls():
    for url in (
        "http://ftp.kotori9.dev/file",
        "http://localhost.evil.example/file",
        "https://user:secret@host/file",
    ):
        with pytest.raises(ValueError):
            validate_url(url, True)
    assert validate_url("http://127.0.0.1:1234/file", True).hostname == "127.0.0.1"
    bad = manifest()
    bad["artifacts"][0]["url"] = "https://evil.example/release.zip"
    with pytest.raises(ValueError):
        parse_manifest(json.dumps(bad), "https://ftp.kotori9.dev/clef-use")


def test_zip_slip_is_refused(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zip:
        zip.writestr("../escaped", "bad")
    with pytest.raises(ValueError, match="unsafe"):
        safe_extract(archive, tmp_path / "destination")
    assert not (tmp_path / "escaped").exists()


def test_windows_directory_access_rejects_malformed_identity_without_mutating_acl(monkeypatch):
    from subprocess import CompletedProcess

    import clef_use.installer as installer

    calls = []

    def identity(argv, **kwargs):
        calls.append(argv)
        return CompletedProcess(argv, 0, stdout='"DOMAIN\\user","S-1-5-21-1 /grant Everyone:F"\n')

    monkeypatch.setenv("SystemRoot", "C:\\Windows")
    monkeypatch.setattr(installer.subprocess, "run", identity)
    with pytest.raises(RuntimeError, match="invalid Windows installation user SID"):
        installer.windows_user_access("owned-installation")
    assert len(calls) == 1


def test_install_bootstraps_pip_without_copying_unix_python(tmp_path, monkeypatch):
    import io
    import os
    import subprocess

    import clef_use.installer as installer

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("requirements.txt", "")
        archive.writestr("wheels/clef_use-0.1.0-py3-none-any.whl", b"fixture")
    payload = buffer.getvalue()
    metadata = manifest()
    artifact = metadata["artifacts"][0]
    artifact["sha256"] = hashlib.sha256(payload).hexdigest()
    responses = {
        "/latest/manifest.json": json.dumps(metadata).encode(),
        "/latest/SHA256SUMS": f"{artifact['sha256']}  release.zip\n".encode(),
        "/releases/0.1.0/release.zip": payload,
    }
    base = "https://ftp.kotori9.dev/clef-use"
    monkeypatch.setenv("CLEF_USE_INSTALL_ROOT", str(tmp_path / "installation"))
    monkeypatch.setenv("CLEF_USE_BIN_DIR", str(tmp_path / "bin"))
    monkeypatch.setattr(installer, "fetch", lambda url, *args: responses[url[len(base) :]])
    monkeypatch.setattr(installer, "select_artifact", lambda _: artifact)
    original_run = subprocess.run
    checked = []

    def install_wheels(argv, **kwargs):
        if "--require-hashes" not in argv:
            return original_run(argv, **kwargs)
        binary = installer.Path(argv[0])
        assert binary.is_symlink() == (os.name != "nt")
        probe = original_run(
            [str(binary), "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "pip " in probe.stdout
        checked.append(binary)
        raise RuntimeError("stop before fixture wheels")

    monkeypatch.setattr(installer.subprocess, "run", install_wheels)
    with pytest.raises(RuntimeError, match="stop before fixture wheels"):
        installer.install()
    assert len(checked) == 1
    assert not list((tmp_path / "installation" / "versions").iterdir())
    assert not (tmp_path / "installation" / "current").exists()
    assert not list((tmp_path / "bin").iterdir())


@pytest.fixture(
    params=[("linux", False), ("linux", True), ("win32", False), ("win32", True)],
    ids=["posix-first", "posix-update", "windows-first", "windows-update"],
)
def activation_installation(tmp_path, monkeypatch, request):
    import contextlib
    import io
    import os
    import shlex
    import subprocess
    import sys
    from types import SimpleNamespace

    import clef_use.installer as installer

    platform, update = request.param
    windows = platform == "win32"
    if os.name == "nt" and not windows:
        pytest.skip("POSIX symlink activation requires a POSIX host")
    root, bindir = tmp_path / "installation", tmp_path / "bin"
    root.mkdir()
    bindir.mkdir()
    launcher = bindir / ("clef-use.cmd" if windows else "clef-use")
    current = root / "current"
    old = root / "versions" / "previous"
    preserved = {}
    for name in ("models/weights", "environments/inference/keep", "config.toml", "state/user-data"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"keep user data: " + name.encode())
        preserved[path] = path.read_bytes()
    if update:
        old.mkdir(parents=True)
        receipt = old / "installed.json"
        receipt.write_text(json.dumps({"version": "0.0.9", "sha256": "b" * 64}))
        preserved[receipt] = receipt.read_bytes()
        if windows:
            launcher.write_text(
                '@echo off\nrem clef-use managed launcher\n@"'
                + str(old / "Scripts/clef-use.exe")
                + '" %*\n'
            )
        else:
            current.symlink_to(old.relative_to(root), target_is_directory=True)
            launcher.write_text(
                "#!/bin/sh\n# clef-use managed launcher\nexec "
                + shlex.quote(str(current / "bin/clef-use"))
                + ' "$@"\n'
            )
    previous_launcher = launcher.read_bytes() if update else None
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("requirements.txt", "")
        archive.writestr("wheels/clef_use-0.1.0-py3-none-any.whl", b"fixture")
    payload = buffer.getvalue()
    metadata = manifest()
    artifact = metadata["artifacts"][0]
    artifact.update(
        platform=platform,
        architecture="x86_64",
        python="3.11",
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    responses = {
        "/latest/manifest.json": json.dumps(metadata).encode(),
        "/latest/SHA256SUMS": f"{artifact['sha256']}  release.zip\n".encode(),
        "/releases/0.1.0/release.zip": payload,
    }
    base = installer.DEFAULT_BASE
    monkeypatch.setenv("CLEF_USE_INSTALL_ROOT", str(root))
    monkeypatch.setenv("CLEF_USE_BIN_DIR", str(bindir))
    monkeypatch.setattr(installer.sys, "platform", platform)
    monkeypatch.setattr(installer, "windows_user_access", lambda _: None)
    monkeypatch.setattr(installer, "install_lock", lambda _: contextlib.nullcontext())
    monkeypatch.setattr(installer, "fetch", lambda url, *args: responses[url[len(base) :]])
    monkeypatch.setattr(installer, "select_artifact", lambda _: artifact)

    class FixtureEnvironment:
        # The regression exercises real filesystem activation, not pip or Windows ACLs.
        def __init__(self, **kwargs):
            pass

        def create(self, staged):
            binary = installer.environment_binary(staged, "clef-use")
            binary.parent.mkdir(parents=True)
            binary.write_text(
                f"#!{sys.executable}\nimport sys\n"
                "if sys.argv[1] == 'version': print('0.1.0')\n"
                "elif sys.argv[1] != 'self-test': raise SystemExit(1)\n"
            )
            binary.chmod(0o755)

    original_run = subprocess.run

    def install_wheels(argv, **kwargs):
        if "--require-hashes" in argv:
            return subprocess.CompletedProcess(argv, 0)
        # Run the fixture script portably, including a simulated Windows .exe on POSIX.
        return original_run([sys.executable, *argv], **kwargs)

    monkeypatch.setattr(installer.venv, "EnvBuilder", FixtureEnvironment)
    monkeypatch.setattr(installer.subprocess, "run", install_wheels)
    return SimpleNamespace(
        installer=installer,
        root=root,
        launcher=launcher,
        current=current,
        old=old,
        windows=windows,
        update=update,
        preserved=preserved,
        previous_launcher=previous_launcher,
    )


def test_interrupt_after_activation_preserves_live_environment(
    activation_installation, monkeypatch
):
    case = activation_installation
    installer = case.installer
    original_replace = installer.os.replace
    switched = []

    def replace_then_interrupt(source, destination):
        original_replace(source, destination)
        if destination == (case.launcher if case.windows else case.current):
            if not case.windows:
                # POSIX launcher creation is earlier than the current symlink switch.
                assert case.current.resolve().is_dir()
            switched.append(destination)
            raise KeyboardInterrupt("immediately after activation")

    monkeypatch.setattr(installer.os, "replace", replace_then_interrupt)
    with pytest.raises(KeyboardInterrupt, match="immediately after activation"):
        installer.install()
    assert len(switched) == 1
    if case.windows:
        import re

        match = re.search(r'^@"([^"\r\n]+)" %\*$', case.launcher.read_text(), re.MULTILINE)
        assert match is not None
        target = match[1]
        if target.startswith("%~dp0"):
            target = str(case.launcher.parent / target[5:])
        active = installer.Path(target).parent.parent.resolve()
    else:
        active = case.current.resolve()
    assert active.is_dir(), "interrupted cleanup deleted the live environment"
    assert active != case.old
    assert json.loads((active / "installed.json").read_text())["version"] == "0.1.0"
    installer.smoke(installer.environment_binary(active, "clef-use"), "0.1.0")
    assert all(path.read_bytes() == data for path, data in case.preserved.items())
    assert not (case.root / ".next").exists()


@pytest.mark.parametrize("failure", [KeyboardInterrupt, RuntimeError])
@pytest.mark.parametrize("point", ["smoke", "activation"])
def test_preactivation_failure_removes_only_staging(
    activation_installation, monkeypatch, failure, point
):
    case = activation_installation
    installer = case.installer
    original_replace = installer.os.replace
    reached = []

    def stop(*args, **kwargs):
        reached.append(point)
        raise failure("before activation")

    def replace_or_stop(source, destination):
        if destination == (case.launcher if case.windows else case.current):
            stop()
        original_replace(source, destination)

    if point == "smoke":
        monkeypatch.setattr(installer, "smoke", stop)
    else:
        monkeypatch.setattr(installer.os, "replace", replace_or_stop)
    with pytest.raises(failure, match="before activation"):
        installer.install()
    assert reached == [point]
    assert set((case.root / "versions").iterdir()) == ({case.old} if case.update else set())
    assert all(path.read_bytes() == data for path, data in case.preserved.items())
    if case.update:
        assert case.launcher.read_bytes() == case.previous_launcher
        if not case.windows:
            assert case.current.resolve() == case.old
    else:
        assert not case.current.exists()
        if case.windows or point == "smoke":
            assert not case.launcher.exists()


def test_generated_bootstraps_embed_canonical_installer():
    import base64
    import re
    import runpy
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    builder = runpy.run_path(str(root / "scripts/build_installer.py"))
    assert (root / "install.sh").read_text() == builder["render"]()
    powershell = (root / "install.ps1").read_text()
    match = re.search(r"FromBase64String\('([^']+)'\)", powershell)
    assert match is not None
    assert base64.b64decode(match[1]) == (root / "src/clef_use/installer.py").read_bytes()


@pytest.mark.parametrize("language", ["en", "ko", "ja", "zh-CN"])
def test_localized_installation_commands_match(language):
    import re
    from pathlib import Path

    docs = Path(__file__).resolve().parents[1] / "docs"
    blocks = re.findall(r"```[^\n]*\n(.*?)```", (docs / language / "INSTALL.md").read_text(), re.S)
    english = re.findall(r"```[^\n]*\n(.*?)```", (docs / "en/INSTALL.md").read_text(), re.S)
    assert blocks[-1] == "clef-use doctor --fix\nclef-use uninstall\n"
    assert blocks == english


@pytest.mark.parametrize(
    ("status", "heading"),
    [
        ("CURRENT", "Already up to date. No installation needed."),
        ("INSTALLED", "Installation complete."),
    ],
)
def test_bootstrap_explains_result_and_next_steps(status, heading, tmp_path, monkeypatch, capsys):
    import os

    import clef_use.installer as installer

    monkeypatch.setattr(installer.sys, "argv", ["installer"])
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ.get("PATH", ""))

    def install(*args, progress=None):
        progress("Checking the latest version...")
        return {"status": status, "version": "0.1.12", "executable": str(tmp_path / "clef-use")}

    monkeypatch.setattr(installer, "install", install)
    monkeypatch.setattr(installer, "ask_model_preparation", lambda: None)
    assert installer.main() == 0
    output = capsys.readouterr()
    assert "Checking the latest version..." in output.out
    assert heading in output.out
    assert "Version: 0.1.12" in output.out
    assert "clef-use doctor" in output.out
    assert "clef-use models prepare --help" in output.out
    assert "Runtime installation" in output.out
    assert "does not download model weights" in output.out
    assert "clef-use models prepare\n" in output.out
    assert "export PATH=" not in output.out
    assert '"status"' not in output.out


def test_bootstrap_json_remains_machine_readable(monkeypatch, capsys):
    import clef_use.installer as installer

    monkeypatch.setattr(installer.sys, "argv", ["installer", "--json"])
    result = {"status": "CURRENT", "version": "0.1.12", "executable": "/fixture/clef-use"}

    def install(*args, progress=None):
        assert progress is None
        return result

    monkeypatch.setattr(installer, "install", install)
    assert installer.main() == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == result
    assert output.err == ""


def test_failed_bootstrap_does_not_print_success(monkeypatch, capsys):
    import clef_use.installer as installer

    monkeypatch.setattr(installer.sys, "argv", ["installer"])

    def install(*args, **kwargs):
        raise ValueError("SHA-256 mismatch; previous installation preserved")

    monkeypatch.setattr(installer, "install", install)
    assert installer.main() == 1
    output = capsys.readouterr()
    assert "Installation complete." not in output.out
    assert "Installation failed." in output.err
    assert "SHA-256 mismatch" in output.err
    assert "Installation complete." not in output.err


@pytest.mark.parametrize(
    ("answer", "expected"),
    [("\n", True), ("y\n", True), ("N\n", False), ("wrong\nn\n", False), ("", None)],
)
def test_model_prompt_uses_terminal_instead_of_piped_stdin(answer, expected, monkeypatch):
    import io

    import clef_use.installer as installer

    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("CLEF_USE_NO_MODEL_PROMPT", raising=False)

    class Terminal(io.StringIO):
        def isatty(self):
            return True

        def close(self):
            pass

    reader, writer = Terminal(answer), Terminal()
    monkeypatch.setattr(
        installer,
        "open",
        lambda path, mode="r", **_: writer if mode == "w" else reader,
        raising=False,
    )
    assert installer.ask_model_preparation() is expected
    assert "Prepare models now? [Y/n]" in writer.getvalue()


@pytest.mark.parametrize(
    ("flags", "answer", "runs"),
    [
        ([], True, True),
        ([], False, False),
        ([], None, False),
        (["--json"], True, False),
        (["--skip-models"], True, False),
        (["--prepare-models"], False, True),
    ],
)
def test_bootstrap_model_selection_and_machine_mode(flags, answer, runs, monkeypatch, capsys):
    import clef_use.installer as installer

    monkeypatch.setattr(installer.sys, "argv", ["installer", *flags])
    monkeypatch.setattr(
        installer,
        "install",
        lambda *_a, **_kw: {
            "status": "CURRENT",
            "version": "0.1.17",
            "executable": "/owned/clef-use",
        },
    )
    asked, calls = [], []

    def ask():
        asked.append(True)
        return answer

    monkeypatch.setattr(installer, "ask_model_preparation", ask)
    monkeypatch.setattr(
        installer,
        "prepare_installed_models",
        lambda executable, json_mode: calls.append((executable, json_mode)) or 0,
    )
    assert installer.main() == 0
    assert bool(calls) == runs
    if flags:
        assert asked == []
    else:
        assert asked == [True]
    if "--json" in flags:
        assert json.loads(capsys.readouterr().out)["status"] == "CURRENT"


def test_preparation_failure_preserves_installed_runtime_message(monkeypatch, capsys):
    from types import SimpleNamespace

    import clef_use.installer as installer

    def unavailable(*_a, **_kw):
        raise OSError("no terminal")

    monkeypatch.setattr(installer, "open", unavailable, raising=False)
    monkeypatch.setattr(
        installer.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(returncode=7)
    )
    assert installer.prepare_installed_models("/owned/runtime") == 7
    assert "runtime is installed" in capsys.readouterr().err


@pytest.mark.parametrize(("name", "value"), [("CI", "true"), ("CLEF_USE_NO_MODEL_PROMPT", "1")])
def test_automation_does_not_open_console_input(name, value, monkeypatch):
    import clef_use.installer as installer

    monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        installer,
        "open",
        lambda *_a, **_kw: pytest.fail("automation opened console"),
        raising=False,
    )
    assert installer.ask_model_preparation() is None


@pytest.mark.parametrize("receipt", ["other_python", "changed", "other_arch", "missing_sum"])
def test_repeat_install_validates_existing_artifact_when_bootstrap_python_changes(
    tmp_path, monkeypatch, receipt
):
    import clef_use.installer as installer

    metadata = manifest()
    selected = metadata["artifacts"][0]
    previous = dict(
        selected,
        filename="previous.zip",
        python="3.12",
        sha256="b" * 64,
        url=selected["url"].replace("release.zip", "previous.zip"),
    )
    if receipt == "other_arch":
        previous["architecture"] = "x86_64"
    metadata["artifacts"].append(previous)
    root = tmp_path / "installation"
    current = root / "current"
    current.mkdir(parents=True)
    digest = "c" * 64 if receipt == "changed" else previous["sha256"]
    (current / "installed.json").write_text(json.dumps({"version": "0.1.0", "sha256": digest}))
    monkeypatch.setenv("CLEF_USE_INSTALL_ROOT", str(root))
    monkeypatch.setenv("CLEF_USE_BIN_DIR", str(tmp_path / "bin"))
    monkeypatch.setattr(installer, "windows_user_access", lambda _: None)
    monkeypatch.setattr(installer, "select_artifact", lambda _: selected)
    sums = f"{selected['sha256']}  release.zip\n"
    if receipt != "missing_sum":
        sums += f"{previous['sha256']}  previous.zip\n"
    monkeypatch.setattr(
        installer,
        "fetch",
        lambda url, *args: (
            json.dumps(metadata).encode() if url.endswith("manifest.json") else sums.encode()
        ),
    )
    smoked = []
    monkeypatch.setattr(installer, "smoke", lambda exe, version: smoked.append(version))
    if receipt == "other_python":
        assert installer.install()["status"] == "CURRENT"
        assert smoked == ["0.1.0"]
    else:
        with pytest.raises(ValueError, match="immutable release changed checksum"):
            installer.install()
        assert not smoked
    assert json.loads((current / "installed.json").read_text())["sha256"] == digest

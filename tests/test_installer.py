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

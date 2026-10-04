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

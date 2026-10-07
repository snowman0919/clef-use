import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "deploy_release", Path(__file__).parents[1] / "scripts/deploy_release.py"
)
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


def site_fixture(path, version="0.1.8"):
    source = path / "releases" / version
    source.mkdir(parents=True)
    latest = path / "latest"
    latest.mkdir()
    artifacts = []
    for platform, architecture, python in sorted(deploy.TARGETS):
        name = f"clef-use-{platform}-{architecture}-{python}.zip"
        data = f"{version}:{name}".encode()
        (source / name).write_bytes(data)
        artifacts.append(
            {
                "filename": name,
                "platform": platform,
                "architecture": architecture,
                "python": python,
                "sha256": hashlib.sha256(data).hexdigest(),
                "url": f"{deploy.DEFAULT_BASE}/releases/{version}/{name}",
            }
        )
    manifest = {"schema_version": 1, "version": version, "artifacts": artifacts}
    for destination in (source, latest):
        (destination / "manifest.json").write_text(json.dumps(manifest))
        (destination / "SHA256SUMS").write_text(
            "".join(f"{a['sha256']}  {a['filename']}\n" for a in artifacts)
        )
    for name in ("install.sh", "install.ps1"):
        (path / name).write_text(version)
        (source / name).write_text(version)
    return path


def local_https(monkeypatch, root):
    monkeypatch.setattr(
        deploy,
        "fetch",
        lambda url: (root / url.removeprefix(deploy.DEFAULT_BASE + "/")).read_bytes(),
    )


def test_complete_release_is_idempotent_and_preserves_history(tmp_path, monkeypatch):
    site = site_fixture(tmp_path / "site")
    root = tmp_path / "public"
    local_https(monkeypatch, root)
    old = root / "releases/0.1.3/keep.zip"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"previous published archive")
    first = deploy.publish(site, root)
    assert first == deploy.publish(site, root)
    assert first["targets"] == 15
    assert old.read_bytes() == b"previous published archive"
    assert (root / "latest/manifest.json").read_bytes() == (
        site / "latest/manifest.json"
    ).read_bytes()


@pytest.mark.parametrize("failure", ["local_checksum", "public_checksum", "immutable_version"])
def test_failed_publication_preserves_current_metadata(tmp_path, monkeypatch, failure):
    old = site_fixture(tmp_path / "old", "0.1.3")
    root = tmp_path / "public"
    local_https(monkeypatch, root)
    deploy.publish(old, root)
    before = {
        name: (root / name).read_bytes()
        for name in ("latest/manifest.json", "latest/SHA256SUMS", "install.sh", "install.ps1")
    }
    site = site_fixture(tmp_path / "new")
    archive = next((site / "releases/0.1.8").glob("*.zip"))
    if failure == "local_checksum":
        archive.write_bytes(b"corrupt")
    elif failure == "public_checksum":
        monkeypatch.setattr(deploy, "fetch", lambda _url: b"incorrect public response")
    else:
        deploy.publish(site, root)
        before = {name: (root / name).read_bytes() for name in before}
        (root / "releases/0.1.8" / archive.name).write_bytes(b"different existing version")
    with pytest.raises(ValueError, match="checksum|immutable"):
        deploy.publish(site, root)
    assert all((root / name).read_bytes() == content for name, content in before.items())


def test_downgrade_is_refused_before_mutation(tmp_path, monkeypatch):
    root = tmp_path / "public"
    local_https(monkeypatch, root)
    deploy.publish(site_fixture(tmp_path / "new"), root)
    before = (root / "latest/manifest.json").read_bytes()
    with pytest.raises(ValueError, match="downgrade"):
        deploy.publish(site_fixture(tmp_path / "old", "0.1.3"), root)
    assert (root / "latest/manifest.json").read_bytes() == before
    assert not (root / "releases/0.1.3").exists()


def test_partial_target_matrix_is_refused(tmp_path):
    site = site_fixture(tmp_path / "site")
    manifest = site / "latest/manifest.json"
    data = json.loads(manifest.read_bytes())
    data["artifacts"].pop()
    manifest.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="15 unique"):
        deploy.publish(site, tmp_path / "public")
    assert not (tmp_path / "public").exists()

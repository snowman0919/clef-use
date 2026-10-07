import json
import sys

import pytest

from clef_use import maintenance
from clef_use.config import Config
from clef_use.installer import environment_binary


def managed_install(tmp_path, monkeypatch):
    if sys.platform == "win32":
        pytest.skip("Unix ownership checks; native Windows removal has separate execution evidence")
    root = tmp_path / "runtime"
    version = root / "versions/0.1.20-test"
    version.mkdir(parents=True)
    (version / "pyvenv.cfg").write_text("home = fixture\n")
    (version / "installed.json").write_text(json.dumps({"version": "0.1.20", "sha256": "a" * 64}))
    exe = environment_binary(version, "clef-use")
    exe.parent.mkdir()
    exe.write_text("fixture")
    (root / "current").symlink_to(version, target_is_directory=True)
    bindir = tmp_path / "bin"
    bindir.mkdir()
    launcher = bindir / "clef-use"
    launcher.write_text(
        f'#!/bin/sh\n# clef-use managed launcher\nexec {root}/current/bin/clef-use "$@"\n'
    )
    monkeypatch.setenv("CLEF_USE_INSTALL_ROOT", str(root))
    monkeypatch.setenv("CLEF_USE_BIN_DIR", str(bindir))
    monkeypatch.setenv("CLEF_USE_STATE_DIR", str(tmp_path / "state"))
    return root, version, launcher


def test_uninstall_preserves_cache_settings_and_unrelated_files(tmp_path, monkeypatch):
    root, version, launcher = managed_install(tmp_path, monkeypatch)
    preserved = [tmp_path / "models", tmp_path / "config.toml", launcher.parent / "another-app"]
    for path in preserved:
        path.write_text("preserve")
    assert maintenance.uninstall()["status"] == "UNINSTALLED"
    assert not version.exists() and not launcher.exists() and not (root / "current").exists()
    assert all(path.read_text() == "preserve" for path in preserved)


@pytest.mark.parametrize("unsafe", ["launcher", "unmanaged", "symlink"])
def test_uninstall_refuses_other_installations(tmp_path, monkeypatch, unsafe):
    root, version, launcher = managed_install(tmp_path, monkeypatch)
    if unsafe == "launcher":
        launcher.write_text("other app")
    elif unsafe == "unmanaged":
        (root / "versions/user-files").mkdir()
    else:
        (root / "versions/external").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        maintenance.uninstall()
    assert version.exists() and launcher.exists()


def test_uninstall_refuses_active_runtime(tmp_path, monkeypatch):
    _, version, launcher = managed_install(tmp_path, monkeypatch)
    endpoint = tmp_path / "state/endpoint.json"
    endpoint.parent.mkdir()
    endpoint.write_text("{}")
    monkeypatch.setattr("clef_use.client.RuntimeClient._send", lambda *_: {"busy": True})
    with pytest.raises(RuntimeError, match="active task"):
        maintenance.uninstall()
    assert version.exists() and launcher.exists()


def readiness(ready=True, source="OBSERVED"):
    return {
        "ready": ready,
        "ml_environments": {"clef": {"ready": ready}, "omni": {"ready": True}},
        "models": [{"available": True}],
        "omni_source": {"ready": source == "OBSERVED", "status": source},
        "dependencies": {"mcp": True},
        "permissions": {},
        "capture": {"status": "OBSERVED"},
    }


def test_fix_reuses_prepare_then_rechecks(monkeypatch):
    reports = iter([readiness(False), readiness(True)])
    monkeypatch.setattr("clef_use.doctor.doctor", lambda *_: next(reports))
    monkeypatch.setattr("clef_use.config.load_config", Config)
    monkeypatch.setattr(maintenance, "stop_idle_runtime", lambda: None)
    calls = []
    monkeypatch.setattr(
        "clef_use.provision.prepare", lambda *a, **k: calls.append((a, k)) or {"status": "PREPARED"}
    )
    result = maintenance.diagnose(fix=True)
    assert len(calls) == 1 and result["ready"]
    assert result["repairs"][0]["status"] == "PREPARED"


@pytest.mark.parametrize("source", ["OBSERVED", "MODIFIED", "REVISION_MISMATCH"])
def test_fix_does_not_reinstall_healthy_or_overwrite_modified_source(monkeypatch, source):
    monkeypatch.setattr("clef_use.doctor.doctor", lambda *_: readiness(source=source))
    monkeypatch.setattr(
        "clef_use.provision.prepare", lambda *_a, **_k: pytest.fail("unexpected prepare")
    )
    report = maintenance.diagnose(fix=True)
    assert not report["repairs"] or report["repairs"][0]["status"] == "MANUAL"


def test_docker_alias_routes_fix_to_diagnostics(monkeypatch, capsys):
    from clef_use.cli import main

    calls = []
    monkeypatch.setattr(maintenance, "diagnose", lambda *a: calls.append(a) or {"ready": False})
    assert main(["docker", "--fix", "--no-capture"]) == 2
    assert calls == [(False, True)]
    assert not json.loads(capsys.readouterr().out)["ready"]


@pytest.mark.parametrize("failure", ["device", "timeout"])
def test_fix_preserves_dependencies_when_device_or_probe_fails(monkeypatch, failure):
    report = readiness(False)
    env = report["ml_environments"]["clef"]
    env.update(
        {"device_operation": "ERROR", "errors": {}}
        if failure == "device"
        else {"reason": "TimeoutExpired"}
    )
    monkeypatch.setattr("clef_use.doctor.doctor", lambda *_: report)
    monkeypatch.setattr(
        "clef_use.provision.prepare",
        lambda *_a, **_k: pytest.fail("device failure is not a missing dependency"),
    )
    result = maintenance.diagnose(fix=True)
    assert result["repairs"][0]["status"] == "MANUAL"
    assert result["manual_actions"] and not result["ready"]

from types import SimpleNamespace

import pytest

from clef_use import deployment_profiles as profiles
from clef_use import native_dependencies as native
from clef_use.config import Config


@pytest.mark.parametrize(
    ("system", "backends"),
    [
        ("macos", {"mps", "cpu"}),
        ("linux", {"cuda", "rocm", "xpu", "cpu"}),
        ("windows", {"cuda", "rocm", "xpu", "cpu"}),
    ],
)
def test_os_backend_contract(system, backends, monkeypatch):
    monkeypatch.setattr(profiles, "host_system", lambda: system)
    monkeypatch.setattr(profiles.platform, "machine", lambda: "arm64")
    for backend in {"cuda", "rocm", "xpu", "mps", "cpu"}:
        name = f"{system}-{backend}"
        if backend in backends:
            assert profiles.resolve_profile(name).backend == backend
            assert Config(ml_profile=name, device=backend).device == backend
        else:
            with pytest.raises(ValueError, match="unsupported"):
                profiles.resolve_profile(name)


def test_profile_rejects_wrong_os_and_conflicting_device(monkeypatch):
    monkeypatch.setattr(profiles, "host_system", lambda: "linux")
    with pytest.raises(ValueError, match="current OS"):
        profiles.resolve_profile("windows-cuda")
    with pytest.raises(ValueError, match="conflicts"):
        profiles.resolve_profile("linux-cuda", "cpu")


def test_mps_rejects_intel_mac(monkeypatch):
    monkeypatch.setattr(profiles, "host_system", lambda: "macos")
    monkeypatch.setattr(profiles.platform, "machine", lambda: "x86_64")
    with pytest.raises(ValueError, match="Apple Silicon"):
        profiles.resolve_profile("macos-mps")


def test_legacy_windows_hip_device_migrates(monkeypatch):
    monkeypatch.setattr(profiles, "host_system", lambda: "windows")
    assert profiles.resolve_profile("windows-rocm", "cuda").backend == "rocm"


@pytest.mark.parametrize("backend", ["cuda", "rocm", "xpu", "mps", "cpu"])
def test_backend_selection_never_silently_falls_back(backend):
    torch = SimpleNamespace(
        cuda=SimpleNamespace(is_available=lambda: backend in {"cuda", "rocm"}),
        version=SimpleNamespace(hip="7.2" if backend == "rocm" else None),
        xpu=SimpleNamespace(is_available=lambda: backend == "xpu"),
        backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: backend == "mps")),
    )
    assert profiles.select_backend(torch, backend) == backend
    assert profiles.torch_device(backend) == ("cuda" if backend == "rocm" else backend)
    for unavailable in {"cuda", "rocm", "xpu", "mps"} - {backend}:
        with pytest.raises(RuntimeError, match="unavailable"):
            profiles.select_backend(torch, unavailable)


def report(url="https://download.pytorch.org/whl/cpu/torch.whl", digest="a" * 64):
    return {
        "install": [
            {
                "download_info": {"url": url, "archive_info": {"hashes": {"sha256": digest}}},
                "metadata": {"name": "torch"},
            }
        ]
    }


def test_native_lock_keeps_exact_artifact_and_hash():
    assert native.report_lock(report()) == (
        "torch @ https://download.pytorch.org/whl/cpu/torch.whl --hash=sha256:" + "a" * 64 + "\n"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://download.pytorch.org/torch.whl",
        "https://untrusted.invalid/torch.whl",
        "https://user:secret@repo.amd.com/torch.whl",
    ],
)
def test_native_lock_refuses_unapproved_origin(url):
    with pytest.raises(ValueError, match="origin"):
        native.report_lock(report(url=url))


def test_native_lock_refuses_missing_hash_or_empty_resolution():
    with pytest.raises(ValueError, match="digest"):
        native.report_lock(report(digest=""))
    with pytest.raises(ValueError, match="no packages"):
        native.report_lock({"install": []})


def test_explicit_prepare_profile_overrides_previous_device(monkeypatch):
    from clef_use.provision import select_profile

    monkeypatch.setattr(profiles, "host_system", lambda: "windows")
    previous = Config(ml_profile="windows-rocm", device="cuda")
    assert select_profile(previous, "windows-cpu") == "windows-cpu"
    assert select_profile(previous, "auto") == "windows-rocm"


@pytest.mark.parametrize("arch", ["gfx1150", "gfx1201", "gfx90a"])
def test_rocm_isa_is_configuration_not_gpu_model(arch):
    from clef_use.provision import resolve_rocm_arch

    assert resolve_rocm_arch(Config(), arch) == arch
    assert resolve_rocm_arch(Config(rocm_arch=arch)) == arch


def test_missing_rocm_isa_refuses_wrong_provider_default(monkeypatch):
    from clef_use import deployment_profiles as provision

    monkeypatch.delenv("ROCM_SDK_TARGET_FAMILY", raising=False)
    monkeypatch.setattr(
        provision.subprocess, "run", lambda *_a, **_kw: SimpleNamespace(returncode=0, stdout="")
    )
    with pytest.raises(ValueError, match="specify --rocm-arch"):
        provision.resolve_rocm_arch(Config())


@pytest.mark.parametrize("name", profiles.PROFILES)
def test_native_install_pins_backend_and_required_windows_isa(tmp_path, monkeypatch, name):
    import json

    python = tmp_path / "env" / "bin" / "python"
    python.parent.mkdir(parents=True)
    lock = tmp_path / "common.txt"
    lock.write_text("pillow==12.3.0 \\\n    --hash=sha256:fixture\n")
    commands = []

    def run(command, **kwargs):
        commands.append((command, kwargs))
        if "--report" in command:
            from pathlib import Path

            Path(command[command.index("--report") + 1]).write_text(json.dumps(report()))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(native.subprocess, "run", run)
    native.install_native(python, profiles.PROFILES[name], {}, lock, rocm_arch="gfx1201")
    resolution, options = commands[0]
    install = commands[1][0]
    assert "--require-hashes" in install and "--no-deps" in install
    assert (python.parent.parent / "clef-use-native-lock.txt").exists()
    if name == "windows-rocm":
        assert "torch[device-gfx1201]==2.11.0+rocm7.14.1" in resolution
        assert "torchvision[device-gfx1201]==0.26.0+rocm7.14.1" in resolution
        assert "rocm[device-gfx1201]==7.14.1" in resolution
        assert options["env"]["ROCM_SDK_TARGET_FAMILY"] == "gfx1201"
        assert not any("gfx1150" in arg for arg in resolution)
    elif name.startswith("macos-"):
        assert "torch==2.11.0" in resolution
    else:
        backend = profiles.PROFILES[name].backend
        assert f"torch==2.11.0+{profiles.INDEX_SUFFIXES[backend]}" in resolution


def test_native_install_accepts_non_utf8_pip_diagnostics(tmp_path, monkeypatch):
    import json
    import subprocess
    import sys

    python = tmp_path / "env" / "bin" / "python"
    python.parent.mkdir(parents=True)
    lock = tmp_path / "common.txt"
    lock.write_text("pillow==12.3.0\n")
    original_run = subprocess.run
    from pathlib import Path

    original_read_text = Path.read_text

    def read_text(path, *args, **kwargs):
        kwargs.setdefault("encoding", "cp1252")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)

    def run(command, **kwargs):
        if "--report" in command:
            from pathlib import Path

            data = report()
            data["install"][0]["metadata"]["description"] = "前"
            Path(command[command.index("--report") + 1]).write_text(
                json.dumps(data, ensure_ascii=False), encoding="utf-8"
            )
        return original_run(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(bytes([141]))"],
            **kwargs,
        )

    monkeypatch.setattr(native.subprocess, "run", run)
    native.install_native(python, profiles.PROFILES["windows-rocm"], {}, lock, rocm_arch="gfx1150")
    assert (python.parent.parent / "clef-use-native-lock.txt").is_file()

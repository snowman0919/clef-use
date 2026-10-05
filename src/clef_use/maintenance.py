from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def stop_idle_runtime():
    from .client import RuntimeClient
    from .config import state_dir

    endpoint = state_dir() / "endpoint.json"
    if not endpoint.exists():
        return
    client = RuntimeClient(start=False)
    try:
        health = client._send("health", {})
    except (OSError, ValueError) as exc:
        raise RuntimeError(
            "Cannot verify the runtime; inspect its endpoint before maintenance"
        ) from exc
    if health.get("busy") or health.get("models_pinned"):
        raise RuntimeError("Finish the active task or release model holds before maintenance")
    client._send("shutdown_idle", {})
    deadline = time.monotonic() + 30
    while endpoint.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    if endpoint.exists():
        raise RuntimeError("Runtime did not stop; installation preserved")


def diagnose(capture=True, fix=False):
    from .config import load_config
    from .doctor import doctor

    report = doctor(capture)
    repairs = []
    needs_prepare = (
        not all(env["ready"] for env in report["ml_environments"].values())
        or not all(model["available"] for model in report["models"])
        or not report["omni_source"]["ready"]
    )
    device_blocked = any(
        not env["ready"]
        and (
            env.get("reason") == "TimeoutExpired"
            or (env.get("device_operation") == "ERROR" and not env.get("errors"))
        )
        for env in report["ml_environments"].values()
    )
    if fix and needs_prepare:
        source_status = report["omni_source"]["status"]
        if device_blocked:
            repairs.append(
                {
                    "status": "MANUAL",
                    "reason": "Check backend, GPU driver or probe timeout; dependencies preserved",
                }
            )
        elif source_status not in {"MISSING", "OBSERVED"}:
            repairs.append(
                {"status": "MANUAL", "reason": "Existing OmniParser source is preserved"}
            )
        elif report.get("deployment_profile", {}).get("status") == "ERROR":
            repairs.append({"status": "MANUAL", "reason": "Resolve the configured backend first"})
        elif not all(report["dependencies"].values()):
            repairs.append(
                {"status": "MANUAL", "reason": "Reinstall the runtime using install.sh/install.ps1"}
            )
        else:
            from .provision import prepare

            print(
                "Repairing model dependencies and missing snapshots...", file=sys.stderr, flush=True
            )
            try:
                stop_idle_runtime()
                config = load_config()
                prepared = prepare(config, quantization=config.quantization)
                repairs.append({"status": prepared["status"], "action": "models prepare"})
            except Exception as exc:
                repairs.append({"status": "ERROR", "reason": str(exc)})
            report = doctor(capture)
    report["repairs"] = repairs
    manual = []
    if not all(report["dependencies"].values()):
        manual.append("Reinstall the runtime using install.sh/install.ps1")
    if (
        report["permissions"].get("screen_capture") is False
        or report["permissions"].get("input_injection") is False
    ):
        manual.append("Grant Screen Recording and Accessibility permission in system settings")
    if sys.platform == "linux" and not os.environ.get("DISPLAY"):
        manual.append("Run from a graphical X11 session; SSH has no DISPLAY")
    elif capture and report["capture"].get("status") != "OBSERVED":
        manual.append("Check the graphical session and screen capture permissions")
    if report.get("windows_desktop", {}).get("status") == "UNAVAILABLE":
        manual.append("Run from the signed-in Windows desktop, not a noninteractive SSH session")
    manual.extend(item["reason"] for item in repairs if item["status"] == "MANUAL")
    report["manual_actions"] = manual
    return report


def _remove_installation(plan):
    root, launcher = Path(plan["root"]), Path(plan["launcher"])
    if hashlib.sha256(launcher.read_bytes()).hexdigest() != plan["launcher_sha256"]:
        raise RuntimeError("Launcher changed; removal refused")
    versions = root / "versions"
    if (
        root.is_symlink()
        or versions.is_symlink()
        or sorted(str(p) for p in versions.iterdir()) != plan["versions"]
    ):
        raise RuntimeError("Installation changed; removal refused")
    for value in plan["versions"]:
        path = Path(value)
        if (
            path.is_symlink()
            or not (path / "installed.json").is_file()
            or not (path / "pyvenv.cfg").is_file()
        ):
            raise RuntimeError("Unmanaged directory found; removal refused")
    launcher.unlink()
    current = root / "current"
    if current.is_symlink():
        current.unlink()
    for value in plan["versions"]:
        shutil.rmtree(value)
    versions.rmdir()
    return {
        "status": "UNINSTALLED",
        "root": str(root),
        "preserved": "model cache, configuration, MCP registrations and PATH",
    }


def uninstall():
    from .installer import environment_binary, install_lock

    prefix = Path(sys.prefix).absolute()
    root = (
        Path(os.environ.get("CLEF_USE_INSTALL_ROOT", prefix.parent.parent)).expanduser().absolute()
    )
    if root.is_symlink() or not (root / "versions").is_dir() or (root / "versions").is_symlink():
        raise ValueError("Only an installer-managed installation can be removed")
    windows = sys.platform == "win32"
    receipt_path = prefix / "installed.json"
    receipt = json.loads(receipt_path.read_text()) if receipt_path.is_file() else {}
    default_bin = (
        Path(receipt["launcher"]).parent
        if "launcher" in receipt
        else (root / "bin" if windows else Path.home() / ".local/bin")
    )
    bindir = Path(os.environ.get("CLEF_USE_BIN_DIR", default_bin)).expanduser().absolute()
    launcher = bindir / ("clef-use.cmd" if windows else "clef-use")
    with install_lock(root / "install.lock"):
        text = launcher.read_text(encoding="utf-8")
        if launcher.is_symlink() or "clef-use managed launcher" not in text:
            raise ValueError("Launcher is not managed by clef-use")
        if windows:
            import re

            match = re.search(r'^@"([^"\r\n]+)" %\*$', text, re.MULTILINE)
            if not match:
                raise ValueError("Managed launcher is malformed")
            target = match[1]
            executable = (
                Path(os.path.normpath(str(bindir / target[5:])))
                if target.startswith("%~dp0")
                else Path(target)
            )
            active = executable.parent.parent
            if executable != environment_binary(active, "clef-use"):
                raise ValueError("Launcher does not target a managed runtime")
        else:
            import shlex

            command = shlex.split(text.splitlines()[-1])
            if command != ["exec", str(root / "current/bin/clef-use"), "$@"]:
                raise ValueError("Launcher belongs to another installation")
            active = (root / "current").resolve()
        versions = sorted((root / "versions").iterdir())
        if active not in versions:
            raise ValueError("Active runtime is outside the managed versions directory")
        for version in versions:
            if (
                version.is_symlink()
                or not (version / "pyvenv.cfg").is_file()
                or not environment_binary(version, "clef-use").is_file()
            ):
                raise ValueError("Unmanaged version directory; installation preserved")
            receipt = json.loads((version / "installed.json").read_text())
            from .installer import release_version

            release_version(receipt["version"])
            if len(receipt.get("sha256", "")) != 64:
                raise ValueError("Invalid installation receipt")
        stop_idle_runtime()
        plan = {
            "root": str(root),
            "launcher": str(launcher),
            "launcher_sha256": hashlib.sha256(launcher.read_bytes()).hexdigest(),
            "versions": [str(p) for p in versions],
        }
        if not windows:
            return _remove_installation(plan)
        # Windows holds the running venv's executables open until this command exits.
        python = Path(sys._base_executable).resolve()
        if python.is_relative_to(root.resolve()):
            raise RuntimeError("An external Python interpreter is required for Windows removal")
        fd, result_path = tempfile.mkstemp(prefix="clef-use-uninstall-", suffix=".json")
        os.close(fd)
        code = (
            Path(__file__).read_text()
            + """
import ctypes
from ctypes import wintypes
kernel = ctypes.windll.kernel32
kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel.CloseHandle.argtypes = [wintypes.HANDLE]
parent = kernel.OpenProcess(0x100000, False, int(sys.argv[1]))
try:
    if parent:
        if kernel.WaitForSingleObject(parent, 30000) != 0:
            raise RuntimeError("Uninstall parent did not exit")
    elif kernel.GetLastError() != 87:
        raise RuntimeError("Cannot verify uninstall parent exit")
    import msvcrt
    plan = json.loads(sys.argv[2])
    with (Path(plan["root"]) / "install.lock").open("a+b") as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        result = _remove_installation(plan)
except Exception as exc:
    result = {"status": "ERROR", "reason": str(exc)}
finally:
    if parent:
        ctypes.windll.kernel32.CloseHandle(parent)
Path(sys.argv[3]).write_text(json.dumps(result), encoding="utf-8")
"""
        )
        subprocess.Popen(
            [str(python), "-c", code, str(os.getpid()), json.dumps(plan), result_path],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        return {
            "status": "UNINSTALL_SCHEDULED",
            "result": result_path,
            "preserved": "model cache, configuration, MCP registrations and PATH",
        }

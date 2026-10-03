from __future__ import annotations

import asyncio
import ctypes
import importlib.util
import json
import subprocess
import sys

from .config import load_config
from .models import inventory


async def mcp_probe():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    parameters = StdioServerParameters(command=sys.executable, args=["-m", "clef_use.cli", "mcp"])
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            return [tool.name for tool in tools.tools]


def mac_permissions():
    if sys.platform != "darwin":
        return {"screen_capture": "NOT_PROBED", "input_injection": "NOT_PROBED"}
    core = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    accessibility = ctypes.CDLL(
        "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
    )
    core.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool
    accessibility.AXIsProcessTrusted.restype = ctypes.c_bool
    return {
        "screen_capture": bool(core.CGPreflightScreenCaptureAccess()),
        "input_injection": bool(accessibility.AXIsProcessTrusted()),
    }


def windows_desktop_probe():
    from .windows_input import WindowsInput

    try:
        return {"status": "OBSERVED", **WindowsInput().desktop_status()}
    except RuntimeError as exc:
        return {"status": "UNAVAILABLE", "reason": str(exc)}


def doctor(capture: bool = True):
    config = load_config()
    permissions = mac_permissions()
    report = {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "dependencies": {
            module: importlib.util.find_spec(module) is not None
            for module in ("mcp", "PIL", "mss", "pyautogui", "pyperclip")
        },
        "models": inventory(config.model_dir, config.decision_model),
        "permissions": permissions,
    }
    if sys.platform == "win32":
        report["windows_desktop"] = windows_desktop_probe()
    python = config.clef_python or sys.executable
    try:
        result = subprocess.run(
            [
                str(python),
                "-c",
                "import torch,json; print(json.dumps({'torch':torch.__version__,"
                "'cuda':torch.cuda.is_available(),'mps':torch.backends.mps.is_available(),"
                "'cpu':True}))",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        report["acceleration"] = (
            json.loads(result.stdout) if result.returncode == 0 else "ML_DEPENDENCIES_MISSING"
        )
    except (OSError, ValueError, subprocess.TimeoutExpired):
        report["acceleration"] = "NOT_RUN"
    if capture and permissions["screen_capture"] is not False:
        try:
            from .backends import DesktopCapture

            frame = DesktopCapture().capture()
            from PIL import ImageStat

            report["capture"] = {
                "status": "OBSERVED",
                "pixels": frame.image.size,
                "logical_size": frame.logical_size,
                "nonuniform": max(ImageStat.Stat(frame.image).stddev) > 1,
            }
        except Exception as exc:
            report["capture"] = {"status": "ERROR", "type": type(exc).__name__}
    else:
        report["capture"] = {"status": "NOT_RUN", "reason": "disabled or permission unavailable"}
    report["input"] = {
        "status": "DESKTOP_CHECK_ONLY" if sys.platform == "win32" else "PERMISSION_CHECK_ONLY",
        "reason": "doctor does not inject input",
    }
    try:
        report["mcp"] = {
            "status": "OBSERVED",
            "tools": asyncio.run(asyncio.wait_for(mcp_probe(), 45)),
        }
    except Exception as exc:
        report["mcp"] = {"status": "ERROR", "type": type(exc).__name__}
    report["models_semantics"] = "NOT_RUN; cache presence is not model inference proof"
    report["ready"] = (
        all(report["dependencies"].values())
        and report["mcp"].get("status") == "OBSERVED"
        and all(m["available"] for m in report["models"])
        and report["capture"].get("status") == "OBSERVED"
        and report["capture"].get("nonuniform", False)
        and permissions["input_injection"] is not False
        and (sys.platform != "win32" or report["windows_desktop"]["status"] == "OBSERVED")
    )
    return report

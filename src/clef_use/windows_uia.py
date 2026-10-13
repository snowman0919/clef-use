"""Read-only, foreground-bound Windows UI Automation observation.

Only the expected foreground window is in scope. This creates no windows and
never reads Name, Value, GetText or password data. The caller must enforce an
outer child-process timeout for a hung native COM provider. No runtime/provider
input authorization is implemented here. TextEdit support establishes a focused
text control, never generic writability. Unsupported composition stays unknown.

ABI source: Microsoft win32metadata UIAutomationClient.h, SHA256
66b00453430cc6884482352ebc0ddf6db3916e38bf5684caba79d6e86aa1f038.
"""

from __future__ import annotations

import argparse
import ctypes as C
import json
import os
import sys
import time
import uuid

HRESULT = C.c_int32
BOOL = C.c_int32
DWORD = C.c_uint32
HANDLE = C.c_void_p


class GUID(C.Structure):
    _fields_ = [
        ("data1", C.c_uint32),
        ("data2", C.c_uint16),
        ("data3", C.c_uint16),
        ("data4", C.c_ubyte * 8),
    ]

    @classmethod
    def parse(cls, value):
        return cls.from_buffer_copy(uuid.UUID(value).bytes_le)


class RECT(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ("left", "top", "right", "bottom")]


class RECORD(C.Structure):
    _fields_ = [("record", HANDLE), ("record_info", HANDLE)]


class VALUE(C.Union):
    _fields_ = [
        ("integer", C.c_int32),
        ("boolean", C.c_int16),
        ("integer64", C.c_int64),
        ("double", C.c_double),
        ("unknown", HANDLE),
        ("record", RECORD),
    ]


class TAGGED_VARIANT(C.Structure):
    _fields_ = [
        ("vt", C.c_uint16),
        ("reserved1", C.c_uint16),
        ("reserved2", C.c_uint16),
        ("reserved3", C.c_uint16),
        ("value", VALUE),
    ]


class VARIANT(C.Union):
    _fields_ = [("tagged", TAGGED_VARIANT), ("decimal", C.c_ubyte * 16)]


CLSID_UIA8 = GUID.parse("e22ad333-b25f-460c-83d0-0581107395c9")
IID_UIA = GUID.parse("30cbe57d-d9d0-452a-ab13-7ac5ac4825ee")
IID_TEXT_EDIT = GUID.parse("17e21576-996c-4870-99d9-bff323380c06")
VT_I4, VT_BOOL = 3, 11
PROCESS_ID, HAS_FOCUS, CONTROL_TYPE = 30002, 30008, 30003
TEXT_EDIT_PATTERN = 10032


class Unavailable(Exception):
    def __init__(self, reason, hresult=None, winerror=None):
        self.reason, self.hresult, self.winerror = reason, hresult, winerror


def hex_hresult(value):
    return f"0x{value & 0xFFFFFFFF:08x}"


def check_abi():
    expected = 24 if C.sizeof(HANDLE) == 8 else 16
    if C.sizeof(VARIANT) != expected or C.sizeof(GUID) != 16 or C.sizeof(RECT) != 16:
        raise Unavailable("native ABI layout mismatch")
    return {"pointer_bytes": C.sizeof(HANDLE), "variant_bytes": C.sizeof(VARIANT)}


def com_method(pointer, slot, restype, *arguments):
    table = C.cast(HANDLE(pointer), C.POINTER(C.POINTER(HANDLE))).contents
    function = C.WINFUNCTYPE(restype, HANDLE, *arguments)(table[slot])
    return lambda *values: function(HANDLE(pointer), *values)


class Session:
    """One MTA thread's DLL bindings and owned returned COM references."""

    def __init__(self, result):
        self.result = result
        self.references = []
        self.initialized = False
        self.previous_dpi = None
        self.user = C.WinDLL("user32", use_last_error=True)
        self.ole = C.WinDLL("ole32", use_last_error=True)
        self.automation = C.WinDLL("oleaut32", use_last_error=True)
        signatures = (
            (self.user, "GetForegroundWindow", [], HANDLE),
            (self.user, "GetWindowThreadProcessId", [HANDLE, C.POINTER(DWORD)], DWORD),
            (self.user, "GetWindowRect", [HANDLE, C.POINTER(RECT)], BOOL),
            (self.user, "SetThreadDpiAwarenessContext", [HANDLE], HANDLE),
            (self.ole, "CoInitializeEx", [HANDLE, DWORD], HRESULT),
            (self.ole, "CoUninitialize", [], None),
            (
                self.ole,
                "CoCreateInstance",
                [C.POINTER(GUID), HANDLE, DWORD, C.POINTER(GUID), C.POINTER(HANDLE)],
                HRESULT,
            ),
            (self.automation, "VariantClear", [C.POINTER(VARIANT)], HRESULT),
        )
        for library, name, arguments, restype in signatures:
            function = getattr(library, name)
            function.argtypes, function.restype = arguments, restype

    def initialize(self):
        hr = self.ole.CoInitializeEx(None, 0)  # COINIT_MULTITHREADED
        self.result["com_initialize_hresult"] = hex_hresult(hr)
        if hr not in (0, 1):  # S_OK and S_FALSE both own one initialization.
            reason = "RPC_E_CHANGED_MODE" if hr & 0xFFFFFFFF == 0x80010106 else "COM unavailable"
            raise Unavailable(reason, hr)
        self.initialized = True
        self.previous_dpi = self.user.SetThreadDpiAwarenessContext(HANDLE(-4))
        if not self.previous_dpi:
            raise Unavailable("physical DPI context unavailable", winerror=C.get_last_error())

    def own(self, pointer):
        if pointer.value:
            # Each returned reference is owned even when pointer values repeat.
            self.references.append(pointer.value)
        return pointer.value

    def create(self):
        pointer = HANDLE()
        hr = self.ole.CoCreateInstance(
            C.byref(CLSID_UIA8), None, 1, C.byref(IID_UIA), C.byref(pointer)
        )  # CLSCTX_INPROC_SERVER
        value = self.own(pointer)
        if hr != 0 or not value:
            raise Unavailable("UI Automation activation unavailable", hr)
        return value

    def returned(self, pointer, slot, *arguments):
        output = HANDLE()
        types, values = zip(*arguments, strict=True) if arguments else ((), ())
        hr = com_method(pointer, slot, HRESULT, *types, C.POINTER(HANDLE))(*values, C.byref(output))
        return hr, self.own(output)

    def require_returned(self, pointer, slot, reason, *arguments):
        hr, output = self.returned(pointer, slot, *arguments)
        if hr != 0 or not output:
            raise Unavailable(reason, hr)
        return output

    def property(self, element, identifier, expected_vt):
        value = VARIANT()  # VT_EMPTY, including before a failed native call.
        try:
            hr = com_method(element, 11, HRESULT, C.c_int32, BOOL, C.POINTER(VARIANT))(
                identifier, 1, C.byref(value)
            )  # ignoreDefaultValue=TRUE
            item = {"hresult": hex_hresult(hr), "vt": value.tagged.vt}
            if hr == 0 and value.tagged.vt == expected_vt:
                if expected_vt == VT_I4:
                    item["value"] = value.tagged.value.integer
                elif expected_vt == VT_BOOL and value.tagged.value.boolean in (-1, 0):
                    item["value"] = value.tagged.value.boolean == -1
            return item
        finally:
            hr = self.automation.VariantClear(C.byref(value))
            if hr != 0:
                self.result["cleanup_errors"].append(
                    {"operation": "VariantClear", "hresult": hex_hresult(hr)}
                )

    def foreground(self, expected, expected_bounds):
        hwnd = self.user.GetForegroundWindow()
        if hwnd != expected:
            # Do not inspect another foreground process/window's properties.
            raise Unavailable("foreground window differs from expected owned window")
        pid, bounds = DWORD(), RECT()
        tid = self.user.GetWindowThreadProcessId(HANDLE(hwnd), C.byref(pid))
        if not tid or not pid.value or not self.user.GetWindowRect(HANDLE(hwnd), C.byref(bounds)):
            raise Unavailable("native foreground identity unavailable", winerror=C.get_last_error())
        rectangle = [bounds.left, bounds.top, bounds.right, bounds.bottom]
        if rectangle[0] >= rectangle[2] or rectangle[1] >= rectangle[3]:
            raise Unavailable("native foreground geometry unavailable")
        if expected_bounds is not None and rectangle != list(expected_bounds):
            raise Unavailable("native foreground bounds differ from expected bounds")
        return {"hwnd": hwnd, "pid": pid.value, "tid": tid, "bounds": rectangle}

    def bind_ancestor(self, uia, focus, expected, expected_pid):
        walker = self.require_returned(uia, 16, "raw UIA parent walker unavailable")
        node = focus
        for depth in range(32):
            process = self.property(node, PROCESS_ID, VT_I4)
            if process.get("value") != expected_pid:
                raise Unavailable("UIA ancestor PID is unverified or differs from native PID")
            hwnd = HANDLE()
            hr = com_method(node, 36, HRESULT, C.POINTER(HANDLE))(C.byref(hwnd))
            if hr != 0:
                raise Unavailable("UIA ancestor native identity unavailable", hr)
            if hwnd.value == expected:
                return depth
            if depth == 31:
                break
            hr, node = self.returned(walker, 3, (HANDLE, HANDLE(node)))
            if hr != 0 or not node:
                raise Unavailable("focus is not bound to expected native window", hr)
        raise Unavailable("UIA ancestor bound exceeded 32 elements")

    def close(self):
        for pointer in reversed(self.references):
            try:
                com_method(pointer, 2, C.c_uint32)()  # IUnknown::Release
            except Exception as error:
                self.result["cleanup_errors"].append(
                    {"operation": "Release", "error_type": type(error).__name__}
                )
        self.references.clear()
        if self.previous_dpi is not None:
            try:
                if not self.user.SetThreadDpiAwarenessContext(HANDLE(self.previous_dpi)):
                    self.result["cleanup_errors"].append(
                        {"operation": "restore_thread_DPI", "winerror": C.get_last_error()}
                    )
            except Exception as error:
                self.result["cleanup_errors"].append(
                    {"operation": "restore_thread_DPI", "error_type": type(error).__name__}
                )
        if self.initialized:
            try:
                self.ole.CoUninitialize()
            except Exception as error:
                self.result["cleanup_errors"].append(
                    {"operation": "CoUninitialize", "error_type": type(error).__name__}
                )
            finally:
                self.initialized = False


def native_observe(expected, result, expected_bounds=None):
    """Acquire synchronously on the caller's non-window-owning MTA thread.

    Native COM providers can hang. The worker's owner must enforce the process
    timeout; no background threads or abandonable acquisitions are created.
    """
    started = time.monotonic()
    result["started_at"] = time.time()
    result["observed_at"] = result["started_at"]
    session = None
    stage = "initialization"
    try:
        result["abi"] = check_abi()
        session = Session(result)
        session.initialize()
        stage = "foreground_before"
        before = session.foreground(expected, expected_bounds)
        result["native_before"] = before
        stage = "UIA_activation"
        uia = session.create()
        stage = "focused_element"
        focus = session.require_returned(uia, 8, "focused UIA element unavailable")
        pid = session.property(focus, PROCESS_ID, VT_I4)
        result["provider_process"] = pid
        if pid.get("value") != before["pid"]:
            raise Unavailable("focused provider PID is unverified or differs from native PID")
        keyboard_focus = session.property(focus, HAS_FOCUS, VT_BOOL)
        result["keyboard_focus"] = keyboard_focus
        if keyboard_focus.get("value") is not True:
            raise Unavailable("focused UIA element lacks verified keyboard focus")
        result["control_type"] = session.property(focus, CONTROL_TYPE, VT_I4)
        stage = "window_binding"
        result["ancestor_depth"] = session.bind_ancestor(uia, focus, expected, before["pid"])
        stage = "TextEdit_pattern"
        pattern_hr, pattern = session.returned(
            focus,
            14,
            (C.c_int32, TEXT_EDIT_PATTERN),
            (C.POINTER(GUID), C.byref(IID_TEXT_EDIT)),
        )
        result["pattern_hresult"] = hex_hresult(pattern_hr)
        result["pattern_supported"] = pattern_hr == 0 and pattern is not None
        result["status"] = "PARTIAL"
        if not result["pattern_supported"]:
            result["reason"] = "TextEdit pattern unavailable; IME remains UNKNOWN"
        else:
            result["text_focus"] = True
            stage = "active_composition"
            hr, composition = session.returned(pattern, 9)
            result["composition"] = {
                "hresult": hex_hresult(hr),
                "range_present": composition is not None if hr == 0 else None,
            }
            if hr == 0:
                result["ime_composing"] = composition is not None
                result["status"] = "VALID"
            else:
                result["reason"] = "active composition query failed; IME remains UNKNOWN"
            stage = "conversion_target_diagnostic"
            target_hr, target = session.returned(pattern, 10)
            result["conversion_target"] = {
                "hresult": hex_hresult(target_hr),
                "range_present": target is not None if target_hr == 0 else None,
                "absence_proof": False,
            }
            if hr == 0 and composition is None and target_hr == 0 and target is not None:
                result["ime_composing"] = None
                result["status"] = "PARTIAL"
                result["reason"] = "composition and conversion-target observations inconsistent"
        stage = "focus_recheck"
        again = session.require_returned(uia, 8, "focused UIA recheck unavailable")
        same = BOOL()
        hr = com_method(uia, 3, HRESULT, HANDLE, HANDLE, C.POINTER(BOOL))(
            HANDLE(focus), HANDLE(again), C.byref(same)
        )
        if hr != 0 or not same.value:
            raise Unavailable("focused UIA element changed during observation", hr)
        stage = "foreground_after"
        after = session.foreground(expected, expected_bounds)
        result["native_after"] = after
        if before != after:
            raise Unavailable("native foreground identity or geometry changed during observation")
    except Unavailable as error:
        result.update(status="UNAVAILABLE", reason=error.reason, failed_stage=stage)
        if error.hresult is not None:
            result["hresult"] = hex_hresult(error.hresult)
        if error.winerror is not None:
            result["winerror"] = error.winerror
        result["text_focus"] = result["ime_composing"] = None
    except Exception as error:
        result.update(status="UNAVAILABLE", error_type=type(error).__name__, failed_stage=stage)
        result["text_focus"] = result["ime_composing"] = None
    finally:
        if session is not None:
            session.close()
        result["completed_at"] = time.time()
        result["acquisition_seconds"] = time.monotonic() - started
        if result["cleanup_errors"]:
            result["status"] = "UNAVAILABLE"
            result["text_focus"] = result["ime_composing"] = None
        if result["acquisition_seconds"] > 0.5:
            result["status_before_stale"] = result["status"]
            result["status"] = "STALE"
            result["text_focus"] = result["ime_composing"] = None


def unavailable(reason):
    return {
        "status": "UNAVAILABLE",
        "scope": "focused_control_only_not_global_IME_or_input_authorization",
        "text_focus": None,
        "ime_composing": None,
        "editable": None,
        "observed_at": None,
        "started_at": None,
        "completed_at": None,
        "acquisition_seconds": None,
        "cleanup_errors": [],
        "reason": reason,
    }


def observe(expected_hwnd: int, expected_bounds=None):
    """Observe only the expected foreground window, synchronously.

    Bounds, when provided, are physical [left, top, right, bottom]. Timestamps
    are wall-clock seconds; observed_at is the conservative acquisition start.
    acquisition_seconds uses a monotonic clock and includes COM cleanup. Facts
    acquired in more than 0.5 seconds are cleared. Returned native identities
    belong only in the caller's private protocol, never public telemetry.
    """
    result = unavailable("observation not acquired")
    if type(expected_hwnd) is not int or not 0 < expected_hwnd < 1 << (8 * C.sizeof(HANDLE)):
        result["reason"] = "expected window must be a positive native HWND"
        return result
    if expected_bounds is not None and (
        not isinstance(expected_bounds, (list, tuple))
        or len(expected_bounds) != 4
        or any(
            type(value) is not int or not -(1 << 31) <= value < 1 << 31 for value in expected_bounds
        )
        or expected_bounds[0] >= expected_bounds[2]
        or expected_bounds[1] >= expected_bounds[3]
    ):
        result["reason"] = "expected bounds must be a nonempty physical native rectangle"
        return result
    if sys.platform != "win32":
        result["reason"] = "Windows native UI Automation required"
        return result
    result.pop("reason")
    native_observe(expected_hwnd, result, expected_bounds)
    return result


def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate request property")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("nonfinite JSON value")


def emit(value):
    print(json.dumps(value, allow_nan=False, separators=(",", ":")), flush=True)


def worker():
    """Private JSONL protocol; caller owns the hard native-call timeout."""
    if sys.platform != "win32":
        emit({"ready": False, "protocol": 1, "reason": "Windows native UI Automation required"})
        return 1
    emit({"ready": True, "protocol": 1, "pid": os.getpid(), "native_initialized": False})
    while line := sys.stdin.buffer.readline(4097):
        if len(line) > 4096:
            emit(unavailable("request exceeds 4096 bytes"))
            return 2
        try:
            request = json.loads(
                line.decode("utf-8"),
                object_pairs_hook=strict_object,
                parse_constant=reject_constant,
            )
            if (
                not isinstance(request, dict)
                or "window" not in request
                or request.keys() - {"window", "bounds"}
                or ("bounds" in request and request["bounds"] is None)
            ):
                raise ValueError("request requires window and optional physical bounds only")
        except (ValueError, UnicodeError, RecursionError):
            emit(unavailable("invalid observation request"))
            continue
        emit(observe(request["window"], request.get("bounds")))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--worker", action="store_true")
    mode.add_argument("--window", type=lambda value: int(value, 0))
    arguments = parser.parse_args()
    if arguments.worker:
        return worker()
    emit(observe(arguments.window))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

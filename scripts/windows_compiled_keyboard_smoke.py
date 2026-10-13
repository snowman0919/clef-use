"""Smoke compiled Windows keyboard input on a disposable owned native RichEdit.

Run with the runtime under validation already selected by the caller. The report
records imported package provenance; this script never overlays or installs it.
Only an already loaded Korean layout is used, on this fixture's own UI thread.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.metadata
import json
import os
import sys
import time
import tkinter as tk
import traceback
from pathlib import Path
from threading import Event, Thread

from windows_gui_support import restore_foreground

import clef_use
from clef_use.backends import DesktopAction, DesktopCapture
from clef_use.input_ir import InputContext, TextInput
from clef_use.runtime import SessionRuntime
from clef_use.schema import ActionCandidate, Observation
from clef_use.state import FactValidity
from clef_use.windows_input import WindowsInput
from clef_use.windows_state import WindowsStateProvider


class FocusInfo(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        *[(n, ctypes.c_void_p) for n in ["active", "focus", "capture", "menu", "move", "caret"]],
        ("rect", ctypes.c_int32 * 4),
    ]


def run(output):
    report = {
        "status": "RUNNING",
        "scope": "compiled native keyboard on disposable owned RichEdit",
        "send_counter_scope": (
            "Calls to WindowsInput._send forwarded unchanged; not OS receiver instrumentation"
        ),
    }
    gui = ui = provider = runtime = None
    previous = owned = edit = None
    second_edit = None
    subclass_library = submit_callback = None
    subclass_installed = False
    ime_restore = None
    native_send_calls = 0

    def cleanup_step(name, function):
        try:
            return function()
        except BaseException as exc:
            report.setdefault("cleanup_errors", []).append({"step": name, "error": repr(exc)})
            report["status"] = "FAIL"
            return None

    try:
        gui = WindowsInput()
        real_native_send = gui._send

        def counted_native_send(*args, **kwargs):
            nonlocal native_send_calls
            native_send_calls += 1
            return real_native_send(*args, **kwargs)

        gui._send = counted_native_send
        previous = gui.foreground()
        ui = tk.Tk()
        ui.title("clef-use owned native editor observation")
        ui.geometry("800x450+120+120")
        ui.update()
        gui.user.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        gui.user.GetAncestor.restype = ctypes.c_void_p
        owned = gui.user.GetAncestor(ui.winfo_id(), 2)
        gui.user.CreateWindowExW.argtypes = [
            ctypes.c_uint32,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        gui.user.CreateWindowExW.restype = ctypes.c_void_p
        gui.user.SetFocus.argtypes = [ctypes.c_void_p]
        gui.user.SetFocus.restype = ctypes.c_void_p
        gui.user.DestroyWindow.argtypes = [ctypes.c_void_p]
        gui.user.IsWindow.argtypes = [ctypes.c_void_p]
        gui.user.IsWindow.restype = ctypes.c_int
        gui.user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        _rich_edit_dll = ctypes.WinDLL("Msftedit.dll")
        edit = gui.user.CreateWindowExW(
            0, "RICHEDIT50W", "", 0x50000004, 20, 20, 700, 350, owned, None, None, None
        )
        report["runtime"] = {
            "distribution_version": importlib.metadata.version("clef-use"),
            "package_version": clef_use.__version__,
            "python": sys.executable,
            "package_file": clef_use.__file__,
            "source_overlay": not Path(clef_use.__file__)
            .resolve()
            .is_relative_to(Path(sys.prefix).resolve()),
        }
        assert edit, "owned native RichEdit creation failed"
        gui.user.SetForegroundWindow(owned)
        gui.user.SetFocus(edit)
        ui.update()
        assert gui.foreground() == owned, "owned editor did not become foreground"
        report["owned_process"] = os.getpid()
        report["owned_window"] = owned

        def pump_call(function):
            result = {}
            timer = [None]

            def invoke():
                try:
                    result["value"] = function()
                except BaseException as exc:
                    result["error"] = exc

            thread = Thread(target=invoke)
            deadline = time.monotonic() + 10

            def poll_completion():
                timer[0] = None
                if thread.is_alive() and time.monotonic() < deadline:
                    timer[0] = ui.after(5, poll_completion)
                else:
                    ui.quit()

            timer[0] = ui.after(5, poll_completion)
            thread.start()
            try:
                ui.mainloop()
            finally:
                if timer[0] is not None:
                    ui.after_cancel(timer[0])
                    timer[0] = None
            assert not thread.is_alive(), "Owned provider/input call exceeded validation bound"
            report.setdefault("owned_after_cleanup", []).append(
                {
                    "owned_callback_pending": timer[0] is not None,
                    "remaining_after_ids": list(ui.tk.call("after", "info")),
                }
            )
            if "error" in result:
                raise result["error"]
            return result["value"]

        class RecordingProvider(WindowsStateProvider):
            def _receive(self, timeout):
                value = super()._receive(timeout)
                if "native_before" in value:
                    report.setdefault("raw_uia_samples", []).append(value)
                return value

        provider = RecordingProvider()
        runtime = SessionRuntime(
            DesktopCapture(), None, None, DesktopAction(gui), state_provider=provider
        )
        report["samples"] = []
        for phase in ["cold", "warm"]:
            state = pump_call(runtime._operation_state)
            report["samples"].append(
                {
                    "phase": phase,
                    "provider": provider.status.copy(),
                    "ime_validity": state.fact("ime_composing").validity.value,
                    "ime_value": state.fact("ime_composing").value,
                    "text_focus": state.fact("text_focus").value,
                    "focused_control": state.fact("focused_control").model_dump(mode="json"),
                    "text_editable": state.fact("text_editable").model_dump(mode="json"),
                }
            )
        assert state.require("text_focus") is True
        assert state.require("ime_composing") is False
        assert state.fact("focused_control").validity == FactValidity.VALID and state.require(
            "focused_control"
        ).get("runtime_id"), "Native focused_control identity not VALID"
        assert (
            state.fact("text_editable").validity == FactValidity.VALID
            and state.require("text_editable") is True
        ), "Native text_editable not VALID/True"
        assert all(
            state.fact(name).validity == FactValidity.UNKNOWN
            for name in ["popup", "modal", "loading", "keymap", "editor", "unit"]
        )
        gui.user.GetGUIThreadInfo.argtypes = [ctypes.c_uint32, ctypes.POINTER(FocusInfo)]
        tid = gui.user.GetWindowThreadProcessId(owned, None)
        frame = runtime.capture.capture()
        literal = "Hi \ud55c\U0001f600"
        literal_observation = Observation("owned-generic-idle-type", frame, ())
        literal_action = ActionCandidate(
            id="owned-generic-literal",
            operation="type",
            observation_id=literal_observation.id,
            target=None,
            description="Owned generic runtime native literal",
            value=literal,
        )
        generic_literal_started = time.perf_counter_ns()
        generic_send_before = native_send_calls
        result = pump_call(
            lambda: runtime._execute_selected(literal_action, literal_observation, Event())
        )
        generic_literal_elapsed = (time.perf_counter_ns() - generic_literal_started) / 1_000_000_000
        ui.update()
        gui.user.GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        text = ctypes.create_unicode_buffer(256)
        gui.user.GetWindowTextW(edit, text, len(text))
        report["generic_idle_literal"] = {
            "status": "PASS" if result.ok and text.value == literal else "FAIL",
            "ok": result.ok,
            "reason": result.reason,
            "route": "SessionRuntime._execute_selected(type,target=None)",
            "elapsed_seconds": generic_literal_elapsed,
            "send_method_calls_delta": native_send_calls - generic_send_before,
            "expected_literal": literal,
            "actual_owned_fixture_text": text.value,
            "actual_is_literal_prefix": literal.startswith(text.value),
            "actual_utf16_units": len(text.value.encode("utf-16-le")) // 2,
            "native_readback_exact": text.value == literal,
            "timeout_policy": "unchanged runtime default; no fixture extension or retry",
        }
        report["literal_readback_exact"] = text.value == literal
        gui.user.GetKeyboardLayoutList.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
        gui.user.GetKeyboardLayoutList.restype = ctypes.c_int
        gui.user.ActivateKeyboardLayout.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        gui.user.ActivateKeyboardLayout.restype = ctypes.c_void_p
        old_hkl = gui.user.GetKeyboardLayout(tid)
        count = gui.user.GetKeyboardLayoutList(0, None)
        layouts = (ctypes.c_void_p * max(1, count))()
        got = gui.user.GetKeyboardLayoutList(count, layouts)
        korean = [h for h in layouts[:got] if h and h & 0xFFFF == 0x412]
        report["active_composition"] = {
            "status": "NOT_RUN",
            "reason": "Existing Korean layout unavailable",
        }
        if korean:
            imm = ctypes.WinDLL("imm32", use_last_error=True)
            imm.ImmGetContext.argtypes = [ctypes.c_void_p]
            imm.ImmGetContext.restype = ctypes.c_void_p
            imm.ImmReleaseContext.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            imm.ImmGetOpenStatus.argtypes = [ctypes.c_void_p]
            imm.ImmSetOpenStatus.argtypes = [ctypes.c_void_p, ctypes.c_int]
            imm.ImmGetConversionStatus.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint32),
                ctypes.POINTER(ctypes.c_uint32),
            ]
            imm.ImmSetConversionStatus.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_uint32,
            ]
            imm.ImmGetCompositionStringW.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.c_uint32,
            ]
            imm.ImmGetCompositionStringW.restype = ctypes.c_int32
            imm.ImmNotifyIME.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_uint32,
                ctypes.c_uint32,
            ]

            def restore_layout_only():
                admitted = bool(gui.user.ActivateKeyboardLayout(old_hkl, 0))
                restored = gui.user.GetKeyboardLayout(tid)
                report["own_thread_layout_restoration"] = {
                    "original": hex(old_hkl),
                    "restored": hex(restored),
                    "admitted": admitted,
                    "readback_exact": restored == old_hkl,
                }
                return admitted and restored == old_hkl

            ime_restore = restore_layout_only
            assert gui.user.ActivateKeyboardLayout(korean[0], 0), (
                "Own thread existing Korean layout activation refused"
            )
            assert gui.user.GetKeyboardLayout(tid) == korean[0], (
                "Own thread Korean layout readback mismatch"
            )
            imc = imm.ImmGetContext(edit)
            assert imc, "Own RichEdit IMM context unavailable"
            conversion = ctypes.c_uint32()
            sentence = ctypes.c_uint32()
            assert imm.ImmGetConversionStatus(imc, ctypes.byref(conversion), ctypes.byref(sentence))
            opened = bool(imm.ImmGetOpenStatus(imc))

            def native_preedit():
                size = imm.ImmGetCompositionStringW(imc, 8, None, 0)
                assert 0 <= size <= 4096, "Owned IMM preedit query outside bound"
                if not size:
                    return b""
                buffer = ctypes.create_string_buffer(size)
                got = imm.ImmGetCompositionStringW(imc, 8, buffer, size)
                assert got == size, "Owned IMM preedit changed during read"
                return ctypes.string_at(buffer, got)

            def restore_ime():
                if native_preedit():
                    assert imm.ImmNotifyIME(imc, 0x15, 4, 0), "Owned preedit cancellation failed"
                a = bool(imm.ImmSetConversionStatus(imc, conversion.value, sentence.value))
                b = bool(imm.ImmSetOpenStatus(imc, opened))
                restored_conversion = ctypes.c_uint32()
                restored_sentence = ctypes.c_uint32()
                got = bool(
                    imm.ImmGetConversionStatus(
                        imc, ctypes.byref(restored_conversion), ctypes.byref(restored_sentence)
                    )
                )
                restored_open = bool(imm.ImmGetOpenStatus(imc))
                exact = (
                    got
                    and restored_conversion.value == conversion.value
                    and restored_sentence.value == sentence.value
                    and restored_open == opened
                )
                report["own_imm_restoration"] = {
                    "original_conversion": conversion.value,
                    "restored_conversion": restored_conversion.value,
                    "original_sentence": sentence.value,
                    "restored_sentence": restored_sentence.value,
                    "original_open": opened,
                    "restored_open": restored_open,
                    "conversion_set_admitted": a,
                    "open_set_admitted": b,
                    "readback_exact": bool(exact),
                    "preedit_cleared": not native_preedit(),
                }
                released = bool(imm.ImmReleaseContext(edit, imc))
                layout_ok = restore_layout_only()
                return bool(
                    a
                    and b
                    and exact
                    and released
                    and layout_ok
                    and report["own_imm_restoration"]["preedit_cleared"]
                )

            ime_restore = restore_ime
            assert imm.ImmSetOpenStatus(imc, True) and imm.ImmGetOpenStatus(imc)
            assert imm.ImmSetConversionStatus(imc, conversion.value | 1, sentence.value)
            gui.keyDown("g", target=owned)
            gui.keyUp("g")
            deadline = time.monotonic() + 1
            while (
                time.monotonic() < deadline and imm.ImmGetCompositionStringW(imc, 8, None, 0) <= 0
            ):
                ui.update()
                time.sleep(0.005)
            preedit_before = native_preedit()
            preedit_length = len(preedit_before)
            assert preedit_length > 0, "Real IME key did not establish owned native preedit"
            composing = pump_call(runtime._operation_state)
            report["active_composition"] = {
                "status": "OBSERVED",
                "native_positive_preedit_bytes": preedit_length,
                "provider": provider.status.copy(),
                "validity": composing.fact("ime_composing").validity.value,
                "value": composing.fact("ime_composing").value,
            }
            assert composing.require("ime_composing") is True, (
                "UIA disagrees with actual native IMM preedit"
            )
            before = ctypes.create_unicode_buffer(256)
            gui.user.GetWindowTextW(edit, before, len(before))

            def active_guard():
                info = FocusInfo()
                info.size = ctypes.sizeof(info)
                if (
                    gui.foreground() != owned
                    or not gui.user.GetGUIThreadInfo(tid, ctypes.byref(info))
                    or info.focus != edit
                ):
                    return False
                fresh = runtime._operation_state()
                return fresh.require("ime_composing") is True and fresh.require(
                    "focused_control"
                ) == composing.require("focused_control")

            primary_send_before = native_send_calls
            rejected_text = pump_call(
                lambda: runtime.action.execute_input(
                    TextInput(text="SHOULD_NOT_APPEAR", method="unicode"),
                    runtime.capture.capture(),
                    Event(),
                    context=InputContext(
                        text_focus=True, ime_composing=composing.require("ime_composing")
                    ),
                    context_guard=active_guard,
                )
            )
            after = ctypes.create_unicode_buffer(256)
            gui.user.GetWindowTextW(edit, after, len(after))
            preedit_after = native_preedit()
            report["active_composition"]["send_method_calls_delta"] = (
                native_send_calls - primary_send_before
            )
            assert native_send_calls == primary_send_before, (
                "Active-IME refusal dispatched native input"
            )
            report["active_composition"].update(
                literal_refused=not rejected_text.ok,
                rejection_reason=rejected_text.reason,
                native_preedit_before_sha256=hashlib.sha256(preedit_before).hexdigest(),
                native_preedit_after_sha256=hashlib.sha256(preedit_after).hexdigest(),
                native_preedit_bytes_exact=preedit_before == preedit_after,
                native_editor_text_exact=before.value == after.value,
            )
            assert (
                not rejected_text.ok
                and rejected_text.reason == "literal insertion requires known idle IME"
                and before.value == after.value
                and preedit_before == preedit_after
            )
            report["active_composition"]["literal_refused_preserving_preedit_and_text"] = True
            report["active_composition"]["status"] = "PASS"

            def assert_unchanged_case(name, call):
                info = FocusInfo()
                info.size = ctypes.sizeof(info)
                assert (
                    gui.foreground() == owned
                    and gui.user.GetGUIThreadInfo(tid, ctypes.byref(info))
                    and info.focus == edit
                ), "Separate refusal case requires owned RichEdit focus"
                pre_before = native_preedit()
                assert pre_before and pre_before == preedit_before, (
                    "Separate refusal case requires original positive native preedit"
                )
                text_before = ctypes.create_unicode_buffer(256)
                gui.user.GetWindowTextW(edit, text_before, len(text_before))
                send_before = native_send_calls
                outcome = pump_call(call)
                ui.update()
                pre_after = native_preedit()
                text_after = ctypes.create_unicode_buffer(256)
                gui.user.GetWindowTextW(edit, text_after, len(text_after))
                report[name] = {
                    "status": "PASS"
                    if not outcome.ok
                    and pre_before == pre_after
                    and text_before.value == text_after.value
                    else "FAIL",
                    "action_ok": outcome.ok,
                    "reason": outcome.reason,
                    "send_method_calls_delta": native_send_calls - send_before,
                    "native_preedit_before_bytes": len(pre_before),
                    "native_preedit_after_bytes": len(pre_after),
                    "native_preedit_before_sha256": hashlib.sha256(pre_before).hexdigest(),
                    "native_preedit_after_sha256": hashlib.sha256(pre_after).hexdigest(),
                    "native_preedit_bytes_exact": pre_before == pre_after,
                    "native_editor_text_exact": text_before.value == text_after.value,
                }
                assert native_send_calls == send_before, name + " dispatched native input"
                assert report[name]["status"] == "PASS", name + " failed: " + outcome.reason
                return outcome

            observation = Observation(
                "owned-native-active-ime-legacy-type", runtime.capture.capture(), ()
            )
            action = ActionCandidate(
                id="owned-literal-ascii",
                operation="type",
                observation_id=observation.id,
                target=None,
                description="Owned native active IME diagnostic",
                value="Z",
            )
            assert_unchanged_case(
                "legacy_type_active_ime",
                lambda: runtime.action.execute(action, observation, Event()),
            )
            generic = assert_unchanged_case(
                "generic_type_active_ime",
                lambda: runtime._execute_selected(action, observation, Event()),
            )
            assert generic.reason == "keyboard input requires known idle IME", generic.reason
            omitted = assert_unchanged_case(
                "direct_input_ir_omitted_context",
                lambda: runtime.action.execute_input(
                    TextInput(text="Z", method="unicode"), runtime.capture.capture(), Event()
                ),
            )
            assert (
                omitted.reason == "native keyboard input requires observed context and a live guard"
            ), omitted.reason
            report["own_ime_restored"] = ime_restore()
            ime_restore = None
            assert report["own_ime_restored"], "Own IMC/layout restoration failed"
        assert report["active_composition"]["status"] == "PASS", report["active_composition"].get(
            "reason"
        )

        def generic_keyboard(operation, value, identity):
            observation = Observation(identity, runtime.capture.capture(), ())
            action = ActionCandidate(
                id=identity,
                operation=operation,
                observation_id=observation.id,
                target=None,
                description="Owned native compiled keyboard regression",
                value=value,
            )
            return pump_call(lambda: runtime._execute_selected(action, observation, Event()))

        gui.ensure_target(owned)
        gui.user.SetFocus(edit)
        ui.update()
        info = FocusInfo()
        info.size = ctypes.sizeof(info)
        assert gui.user.GetGUIThreadInfo(tid, ctypes.byref(info)) and info.focus == edit
        gui.user.SendMessageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
        ]
        gui.user.SendMessageW.restype = ctypes.c_ssize_t
        before_selection = ctypes.create_unicode_buffer(256)
        gui.user.GetWindowTextW(edit, before_selection, len(before_selection))
        report["native_text_after_ime_restoration"] = before_selection.value
        assert before_selection.value == literal, "Own editor text changed during IME restoration"
        selected = generic_keyboard("hotkey", "ctrl+a", "owned-native-select-all")
        start, end = ctypes.c_uint32(), ctypes.c_uint32()
        gui.user.SendMessageW(edit, 0x00B0, ctypes.addressof(start), ctypes.addressof(end))
        selected_text = ctypes.create_unicode_buffer(256)
        gui.user.SendMessageW(edit, 0x043E, 0, ctypes.addressof(selected_text))  # EM_GETSELTEXT
        expected_units = len(literal.encode("utf-16-le")) // 2
        # RichEdit's TOM story retains a final paragraph mark. Native select-all
        # may include it; selected content must still match our complete literal.
        # https://learn.microsoft.com/en-us/windows/win32/api/tom/nn-tom-itextrange
        selection_exact = (
            start.value == 0
            and end.value in (expected_units, expected_units + 1)
            and selected_text.value in (literal, literal + "\r")
        )
        report["generic_select_all"] = {
            "status": "PASS" if selected.ok and selection_exact else "FAIL",
            "ok": selected.ok,
            "reason": selected.reason,
            "native_em_getsel": [start.value, end.value],
            "literal_utf16_units": expected_units,
            "native_selected_text": selected_text.value,
            "native_selection_covers_exact_literal": selection_exact,
            "native_final_paragraph_mark_in_range": end.value == expected_units + 1,
        }
        assert report["generic_select_all"]["status"] == "PASS", selected.reason
        deleted = generic_keyboard("press", "backspace", "owned-native-delete-selection")
        text = ctypes.create_unicode_buffer(256)
        gui.user.GetWindowTextW(edit, text, len(text))
        report["generic_delete_selection"] = {
            "status": "PASS" if deleted.ok and text.value == "" else "FAIL",
            "ok": deleted.ok,
            "reason": deleted.reason,
            "native_editor_empty": text.value == "",
        }
        assert report["generic_delete_selection"]["status"] == "PASS", deleted.reason

        report["generic_submit_focus_transition"] = {"status": "NOT_RUN"}
        second_edit = gui.user.CreateWindowExW(
            0, "RICHEDIT50W", "", 0x50000004, 20, 375, 700, 40, owned, None, None, None
        )
        assert second_edit, "Second owned RichEdit creation failed"
        subclass_library = ctypes.WinDLL("comctl32", use_last_error=True)
        subclass_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
            ctypes.c_size_t,
            ctypes.c_size_t,
        )
        subclass_library.SetWindowSubclass.argtypes = [
            ctypes.c_void_p,
            subclass_type,
            ctypes.c_size_t,
            ctypes.c_size_t,
        ]
        subclass_library.SetWindowSubclass.restype = ctypes.c_int
        subclass_library.RemoveWindowSubclass.argtypes = [
            ctypes.c_void_p,
            subclass_type,
            ctypes.c_size_t,
        ]
        subclass_library.RemoveWindowSubclass.restype = ctypes.c_int
        subclass_library.DefSubclassProc.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_size_t,
            ctypes.c_ssize_t,
        ]
        subclass_library.DefSubclassProc.restype = ctypes.c_ssize_t
        submit_events = []
        submit_errors = []

        @subclass_type
        def submit_callback(hwnd, message, wparam, lparam, subclass_id, reference):
            if message == 0x0100 and wparam == 0x0D:  # WM_KEYDOWN, VK_RETURN
                try:
                    focus_info = FocusInfo()
                    focus_info.size = ctypes.sizeof(focus_info)
                    before = bool(
                        gui.foreground() == owned
                        and gui.user.GetGUIThreadInfo(tid, ctypes.byref(focus_info))
                        and focus_info.focus == edit
                    )
                    if not before:
                        raise RuntimeError("Owned submit receiver focus changed before delivery")
                    gui.user.SetFocus(second_edit)
                    after = bool(
                        gui.user.GetGUIThreadInfo(tid, ctypes.byref(focus_info))
                        and focus_info.focus == second_edit
                    )
                    submit_events.append(
                        {
                            "first_control_focused_before": before,
                            "second_control_focused_after": after,
                            "repeated_keydown": bool(lparam & (1 << 30)),
                        }
                    )
                except BaseException as exc:
                    submit_errors.append(repr(exc))
                return 0
            if message == 0x0102 and wparam == 0x0D:  # Suppress the owned submit's WM_CHAR.
                return 0
            return subclass_library.DefSubclassProc(hwnd, message, wparam, lparam)

        subclass_installed = bool(subclass_library.SetWindowSubclass(edit, submit_callback, 1, 0))
        if subclass_installed:
            # Finish painting the newly created receiver before capturing the
            # observation used by the runtime's unchanged visual-context guard.
            gui.ensure_target(owned)
            gui.user.SetFocus(edit)
            ui.update()
            send_before = native_send_calls
            submitted = generic_keyboard("press", "enter", "owned-native-submit-focus-change")
            info = FocusInfo()
            info.size = ctypes.sizeof(info)
            second_focused = bool(
                gui.user.GetGUIThreadInfo(tid, ctypes.byref(info)) and info.focus == second_edit
            )
            first_text, second_text = (
                ctypes.create_unicode_buffer(256),
                ctypes.create_unicode_buffer(256),
            )
            gui.user.GetWindowTextW(edit, first_text, len(first_text))
            gui.user.GetWindowTextW(second_edit, second_text, len(second_text))
            gui.user.GetAsyncKeyState.argtypes = [ctypes.c_int]
            gui.user.GetAsyncKeyState.restype = ctypes.c_short
            released = bool(
                not (gui.user.GetAsyncKeyState(0x0D) & 0x8000)
                and not gui.key_events
                and not runtime.action.keys
                and not runtime.action.input_executor.owned
            )
            delivery = submitted.delivery.model_dump(mode="json") if submitted.delivery else None
            passed = bool(
                submitted.ok
                and delivery
                and delivery["kind"] == "key"
                and delivery["keys"] == ["enter"]
                and len(submit_events) == 1
                and submit_events[0]["first_control_focused_before"]
                and submit_events[0]["second_control_focused_after"]
                and not submit_events[0]["repeated_keydown"]
                and not submit_errors
                and second_focused
                and first_text.value == second_text.value == ""
                and released
                and native_send_calls - send_before == 2
            )
            report["generic_submit_focus_transition"] = {
                "status": "PASS" if passed else "FAIL",
                "scope": "input delivery and native focus transition, not goal completion",
                "ok": submitted.ok,
                "reason": submitted.reason,
                "delivery": delivery,
                "native_submit_events": submit_events,
                "native_callback_errors": submit_errors,
                "second_control_focused": second_focused,
                "both_owned_controls_empty": first_text.value == second_text.value == "",
                "owned_keys_and_native_enter_released": released,
                "send_method_calls_delta": native_send_calls - send_before,
            }
            assert passed, submitted.reason
        else:
            report["generic_submit_focus_transition"]["reason"] = (
                "SetWindowSubclass failed with native error " + str(ctypes.get_last_error())
            )
        report["initial_literal_utf16_units"] = len(literal.encode("utf-16-le")) // 2
        report["fixture_pump"] = (
            "canonical Tk mainloop; ui.after(5) completion poll; ten-second fixture bound; "
            "unchanged runtime default deadline"
        )
        report["scope"] = (
            "Windows UIA -> State Compiler -> compiled native keyboard on owned RichEdit; "
            "no model or Blender operation success claim"
        )
        from clef_use.operations import OperationRunner, parse_operation_request

        rejected = pump_call(
            lambda: OperationRunner(
                runtime._operation_state, runtime._operation_input, text_method="unicode"
            ).run(parse_operation_request({"family": "menu_assess", "menu": "File"}), Event())
        )
        assert rejected.status == "BLOCKED" and rejected.input_count == 0
        report["unsupported_blender_operation"] = {
            "status": rejected.status,
            "input_count": rejected.input_count,
            "reason": rejected.reason,
        }
        old_process = provider.process
        provider.close()
        report["uia_worker_exited"] = old_process.poll() is not None
        report["status"] = (
            "OBSERVED"
            if report["generic_idle_literal"]["status"] == "PASS"
            and report["generic_submit_focus_transition"]["status"] == "PASS"
            else "FAIL"
        )
    except BaseException:
        report["status"] = "FAIL"
        report["error"] = traceback.format_exc()
    finally:
        if ime_restore is not None:
            report["own_ime_restored"] = cleanup_step("IMM/layout restoration", ime_restore)
            if report["own_ime_restored"] is not True:
                report["status"] = "FAIL"
        if runtime is not None:
            cleanup_step("owned input release", runtime.action.release)
            executor = runtime.action.input_executor
            if executor is not None and executor.guardian is not None:
                guardian = executor.guardian
                cleanup_step("guardian stdin close", guardian.stdin.close)
                cleanup_step("guardian exit", lambda: guardian.wait(timeout=3))
                report["guardian_exited"] = guardian.poll() is not None
        if provider is not None:
            worker = provider.process
            cleanup_step("UIA worker close", provider.close)
            if worker is not None:
                report["uia_worker_exited"] = worker.poll() is not None
        report["cleanup"] = {}
        if gui is not None and ui is not None and owned:
            if gui.foreground() == owned:
                restored = cleanup_step(
                    "foreground restoration", lambda: restore_foreground(ui, gui, previous, owned)
                )
                if restored is not None:
                    report["cleanup"].update(restored)
            else:
                report["cleanup"]["foreground_restored"] = gui.foreground() == previous
        if gui is not None and edit:
            if subclass_installed:
                report["owned_subclass_removed"] = bool(
                    cleanup_step(
                        "owned submit subclass removal",
                        lambda: subclass_library.RemoveWindowSubclass(edit, submit_callback, 1),
                    )
                )
                if not report["owned_subclass_removed"]:
                    report["status"] = "FAIL"
            cleanup_step("owned RichEdit close", lambda: gui.user.DestroyWindow(edit))
        if gui is not None and second_edit:
            cleanup_step("second owned RichEdit close", lambda: gui.user.DestroyWindow(second_edit))
        if ui is not None:
            cleanup_step("owned Tk window close", ui.destroy)
        if gui is not None:
            report["cleanup"]["owned_window_closed"] = (
                not (owned and gui.user.IsWindow(owned))
                and not (edit and gui.user.IsWindow(edit))
                and not (second_edit and gui.user.IsWindow(second_edit))
            )
            report["cleanup"]["native_owned_keys_released"] = (
                not gui.key_events and not gui.unicode_units
            )
        required_cleanup = [
            "foreground_restored",
            "owned_window_closed",
            "native_owned_keys_released",
        ]
        if any(report["cleanup"].get(name) is not True for name in required_cleanup):
            report["status"] = "FAIL"
        if any(report.get(name) is False for name in ("uia_worker_exited", "guardian_exited")):
            report["status"] = "FAIL"
        report["send_method_calls_observed"] = native_send_calls
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps({"status": report["status"], "report": str(args.output)}), flush=True)
    return 0 if report["status"] == "OBSERVED" else 1


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("This owned native keyboard smoke requires Windows.")
    raise SystemExit(main())

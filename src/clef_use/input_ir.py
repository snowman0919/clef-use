"""Typed local OS input, separate from instruction-only Agent Skills.

The watcher runs independently of decision/observation workers. Native devices also
use a child guardian which releases acknowledged ownership on parent pipe EOF or
deadline. It cannot defeat a locked desktop, permissions loss or an OS call that
never returns, and a process death between injection and acknowledgement remains
an explicitly limited recovery window.
"""

from __future__ import annotations

import json
import math
import os
import queue
import subprocess
import sys
import threading
import time
import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

MODIFIERS = frozenset({"ctrl", "shift", "alt", "command"})
KEYS = (
    frozenset("abcdefghijklmnopqrstuvwxyz0123456789")
    | MODIFIERS
    | frozenset(
        {
            "enter",
            "escape",
            "tab",
            "backspace",
            "delete",
            "space",
            "left",
            "right",
            "up",
            "down",
            "home",
            "end",
            "pageup",
            "pagedown",
            "insert",
            "minus",
            "equal",
            "period",
            "comma",
            "slash",
            "backslash",
            "semicolon",
            "apostrophe",
            "bracketleft",
            "bracketright",
            "grave",
        }
    )
    | frozenset(f"f{i}" for i in range(1, 25))
)
Button = Literal["left", "right", "middle"]
Point = tuple[float, float]
KEY_ALIASES = {
    "minus": "-",
    "equal": "=",
    "period": ".",
    "comma": ",",
    "slash": "/",
    "backslash": "\\",
    "semicolon": ";",
    "apostrophe": "'",
    "bracketleft": "[",
    "bracketright": "]",
    "grave": "`",
}


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class InputContext(InputModel):
    lease_id: str | None = None
    state_version: str | None = None
    foreground: str | int | None = None
    editor: str | None = None
    mode: str | None = None
    keymap: str | None = None
    text_focus: bool | None = None
    ime_composing: bool | None = None
    text_control: Literal["select_all", "submit"] | None = None


class KeyInput(InputModel):
    kind: Literal["key"] = "key"
    phase: Literal["tap", "down", "up"] = "tap"
    key: str
    physical_code: int | None = Field(default=None, ge=0, le=65535)
    repeat: int = Field(default=1, ge=1, le=20)
    hold_seconds: float = Field(default=0, ge=0, le=2)

    @field_validator("key")
    @classmethod
    def key_supported(cls, value):
        if value not in KEYS:
            raise ValueError("unsupported logical key")
        return value

    @model_validator(mode="after")
    def hold_policy(self):
        if self.phase != "tap" and (self.repeat != 1 or self.hold_seconds):
            raise ValueError("repeat/hold duration only apply to taps")
        return self


class ChordInput(InputModel):
    kind: Literal["chord"] = "chord"
    modifiers: tuple[str, ...]
    key: str

    @model_validator(mode="after")
    def ordered_chord(self):
        if (
            not self.modifiers
            or len(set(self.modifiers)) != len(self.modifiers)
            or not set(self.modifiers) <= MODIFIERS
        ):
            raise ValueError("ordered unique modifiers required")
        if self.key not in KEYS or self.key in MODIFIERS:
            raise ValueError("chord requires a non-modifier logical key")
        return self


class TextInput(InputModel):
    kind: Literal["text"] = "text"
    text: str = Field(max_length=10000)
    method: Literal["unicode", "clipboard"] = "unicode"

    @field_validator("text")
    @classmethod
    def literal_only(cls, value):
        if any(ord(c) < 32 or 0x7F <= ord(c) < 0xA0 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise ValueError("control characters and isolated surrogates refused")
        return value


def checked_point(point):
    if any(not math.isfinite(v) or not 0 <= v <= 1 for v in point):
        raise ValueError("normalized point outside desktop")
    return point


class PointerInput(InputModel):
    kind: Literal["pointer"] = "pointer"
    phase: Literal["move", "down", "up", "click"] = "click"
    point: Point | None = None
    button: Button = "left"

    @model_validator(mode="after")
    def point_required(self):
        if self.point is not None:
            checked_point(self.point)
        elif self.phase != "up":
            raise ValueError("pointer phase requires a normalized point")
        return self


class GestureInput(InputModel):
    kind: Literal["gesture"] = "gesture"
    points: tuple[Point, ...] = Field(min_length=2, max_length=64)
    surface: tuple[float, float, float, float]
    modifiers: tuple[str, ...] = ()
    button: Button = "left"
    duration: float = Field(gt=0, le=2)

    @model_validator(mode="after")
    def bounded_gesture(self):
        x1, y1, x2, y2 = self.surface
        checked_point((x1, y1))
        checked_point((x2, y2))
        if x1 >= x2 or y1 >= y2:
            raise ValueError("empty gesture surface")
        for point in self.points:
            checked_point(point)
            if not x1 <= point[0] <= x2 or not y1 <= point[1] <= y2:
                raise ValueError("gesture leaves its bounded surface")
        if len(set(self.modifiers)) != len(self.modifiers) or not set(self.modifiers) <= MODIFIERS:
            raise ValueError("ordered unique modifiers required")
        return self


class WheelInput(InputModel):
    kind: Literal["wheel"] = "wheel"
    point: Point
    axis: Literal["vertical", "horizontal"] = "vertical"
    amount: int = Field(ge=-20, le=20)

    @field_validator("point")
    @classmethod
    def valid_point(cls, value):
        return checked_point(value)


InputCommand = Annotated[
    KeyInput | ChordInput | TextInput | PointerInput | GestureInput | WheelInput,
    Field(discriminator="kind"),
]
INPUT_ADAPTER = TypeAdapter(InputCommand)


class InputInterrupted(RuntimeError):
    pass


class InputDispatchError(RuntimeError):
    def __init__(self, message, delivery):
        super().__init__(message)
        self.delivery = delivery


class InputExecutor:
    """Serializes injection while allowing cancellation outside the worker lock."""

    def __init__(self, gui, keys=None, buttons=None):
        self.gui = gui
        self.keys = keys if keys is not None else set()
        self.buttons = buttons if buttons is not None else set()
        self.owned = []
        self.lock = threading.RLock()
        self.execution_lock = threading.Lock()
        self.watch = None
        self.guardian = None
        self.recovery_error = None
        self.active = False
        self.disabled = False
        self.delivery = None
        self.x11_state = None
        self.x11_keys = {}
        self.x11_buttons = {}
        self.x11_keymap = None
        if getattr(gui, "__name__", "") == "pyautogui" and sys.platform == "linux":
            # This is the map used to construct PyAutoGUI's fixed logical
            # keycodes, not a new snapshot taken after an OS layout change.
            self.x11_keymap = tuple(tuple(row) for row in gui.platformModule._display._keymap_codes)
        if self._native():
            self.gui.ownership_changed = self._native_ownership_changed

    def _native_ownership_changed(self):
        try:
            self._sync()
        except RuntimeError:
            # Preserve the successful OS acknowledgement. Cancellation below
            # makes the executor clean up that actual ownership before returning.
            if self.watch:
                self.watch[0].set()

    def _disable_guardian(self):
        self.disabled = True
        self.recovery_error = "native input guardian unavailable"
        process, self.guardian = self.guardian, None
        if process:
            for stream in (process.stdin, process.stdout):
                if stream:
                    try:
                        stream.close()
                    except OSError:
                        pass

    def _native(self):
        from .windows_input import WindowsInput

        return isinstance(self.gui, WindowsInput)

    def _x11_state(self):
        if self.x11_state is not None:
            return self.x11_state
        with self.lock:
            if self.x11_state is None:
                from .x11_input_state import X11InputState

                self.x11_state = X11InputState(self.gui.platformModule._display.get_display_name())
            return self.x11_state

    def _guardian_start(self):
        if self.disabled:
            raise RuntimeError("native input guardian unavailable; input executor disabled")
        # Custom devices are deterministic unit fixtures, never live input sources.
        if self.guardian is None and (
            self._native() or getattr(self.gui, "__name__", "") == "pyautogui"
        ):
            if self._native() and sys.platform != "win32":
                return
            self.guardian = subprocess.Popen(
                [sys.executable, "-m", "clef_use.input_ir", "--guardian"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                close_fds=True,
            )
            ready = queue.Queue()

            def await_ready():
                for line in self.guardian.stdout:
                    if line.strip() == "ready":
                        ready.put("ready")
                        return
                ready.put("unavailable")

            threading.Thread(target=await_ready, daemon=True).start()
            try:
                if ready.get(timeout=3).strip() != "ready":
                    raise RuntimeError("native input guardian unavailable")
            except queue.Empty as exc:
                self.guardian.terminate()
                raise RuntimeError("native input guardian startup timed out") from exc

    def _sync(self):
        process = self.guardian
        if process is not None:
            native_keys = {}
            units = []
            if self._native():
                native_keys = {
                    key: [event.keyboard.vk, event.keyboard.scan, event.keyboard.flags]
                    for key, event in self.gui.key_events.items()
                }
                units = sorted(self.gui.unicode_units)
            try:
                process.stdin.write(
                    json.dumps(
                        {
                            "owned": self.owned,
                            "deadline": self.watch[1] if self.watch else None,
                            "native_keys": native_keys,
                            "unicode_units": units,
                            "x11_keys": self.x11_keys,
                            "x11_buttons": self.x11_buttons,
                        }
                    )
                    + "\n"
                )
                process.stdin.flush()
            except (OSError, ValueError) as exc:
                self._disable_guardian()
                if self.watch:
                    self.watch[0].set()
                raise RuntimeError("native input guardian disconnected") from exc

    def _arm(self, cancelled, deadline, guard, frame):
        try:
            self._guardian_start()
            self.watch = (cancelled, deadline, guard)
            self._sync()
        except Exception:
            self._disable_guardian()
            cancelled.set()
            self.release()
            raise
        watch = self.watch

        def monitor():
            while self.watch is watch:
                reason = None
                if cancelled.wait(0.01):
                    reason = "cancelled"
                elif self.guardian is not None and self.guardian.poll() is not None:
                    reason = "native input guardian disconnected"
                    self._disable_guardian()
                elif time.monotonic() >= deadline:
                    reason = "input deadline expired"
                else:
                    try:
                        self._check(cancelled, deadline, guard, frame)
                    except Exception:
                        reason = "input context changed"
                if reason:
                    with self.lock:
                        if self.watch is not watch:
                            return
                        try:
                            self.release()
                        except Exception as exc:
                            self.recovery_error = type(exc).__name__
                        cancelled.set()
                    return

        threading.Thread(target=monitor, name="clef-input-watchdog", daemon=True).start()

    def _check(self, cancelled, deadline, guard, frame):
        if cancelled.is_set() or time.monotonic() >= deadline:
            raise InputInterrupted("input cancelled or deadline expired")
        if guard:
            if guard() is False:
                raise InputInterrupted("input context guard refused current state")
        if self._native():
            if frame.foreground_window is None:
                raise InputInterrupted("foreground input target unknown")
            self.gui.ensure_target(frame.foreground_window)
            if (
                frame.foreground_bounds is not None
                and self.gui.window_rect(frame.foreground_window) != frame.foreground_bounds
            ):
                raise InputInterrupted("foreground geometry changed")
        elif getattr(self.gui, "__name__", "") == "pyautogui" and sys.platform == "linux":
            window, bounds = self._x11_state().foreground()
            if frame.foreground_window is None or window != frame.foreground_window:
                raise InputInterrupted("foreground changed or unknown")
            if frame.foreground_bounds is not None and bounds != frame.foreground_bounds:
                raise InputInterrupted("foreground geometry changed")
            with self.lock:
                for key, code in self.x11_keys.items():
                    self._x11_keycode(key, code)
        elif getattr(self.gui, "__name__", "") == "pyautogui":
            raise InputInterrupted(
                "typed input foreground verification unavailable on this platform"
            )
        if self._unexpected_input():
            raise InputInterrupted("unowned input held; user intervention or source conflict")
        # State providers and native queries may take longer than the lease.
        # Their successful result cannot renew cancellation/deadline authority.
        if cancelled.is_set() or time.monotonic() >= deadline:
            raise InputInterrupted("input cancelled or deadline expired")

    def _unexpected_input(self):
        with self.lock:
            if self._native():
                return self.gui.unowned_input(self.keys, self.buttons)
            if getattr(self.gui, "__name__", "") != "pyautogui" or sys.platform != "linux":
                return False
            from Xlib import X

            with self._x11_state().query() as connection:
                bitmap = connection.query_keymap()
                held = {code for code in range(256) if bitmap[code // 8] & (1 << (code % 8))}
                owned = set(self.x11_keys.values())
                if held - owned:
                    return True
                mask = connection.screen().root.query_pointer().mask
                for button, bit in (
                    ("left", X.Button1Mask),
                    ("middle", X.Button2Mask),
                    ("right", X.Button3Mask),
                    (4, X.Button4Mask),
                    (5, X.Button5Mask),
                ):
                    if mask & bit and button not in self.buttons:
                        return True
                return False

    def _held(self, key=None, button=None):
        if key is not None and hasattr(self.gui, "is_pressed"):
            return self.gui.is_pressed(key)
        if button is not None and hasattr(self.gui, "button_pressed"):
            return self.gui.button_pressed(button)
        if getattr(self.gui, "__name__", "") == "pyautogui" and sys.platform == "linux":
            from Xlib import X

            with self._x11_state().query() as connection:
                if key is not None:
                    code = self.gui.platformModule.keyboardMapping.get(KEY_ALIASES.get(key, key))
                    if not code:
                        raise InputInterrupted("logical key unavailable in current OS keymap")
                    bitmap = connection.query_keymap()
                    return bool(bitmap[code // 8] & (1 << (code % 8)))
                mask = {
                    "left": X.Button1Mask,
                    "middle": X.Button2Mask,
                    "right": X.Button3Mask,
                    4: X.Button4Mask,
                    5: X.Button5Mask,
                }.get(button, 0)
                return bool(connection.screen().root.query_pointer().mask & mask)
        return False

    def _x11_keycode(self, key, code=None):
        if code is None:
            code = self.gui.platformModule.keyboardMapping.get(KEY_ALIASES.get(key, key))
        if not code or not self._x11_state().binding_matches(code, self.x11_keymap[code]):
            raise InputInterrupted("logical key binding changed in current OS keymap")
        return code

    def _key_down(self, key, frame, acknowledged=None):
        with self.lock:
            if key in self.keys:
                raise InputInterrupted("key already owned; repeat requires explicit tap policy")
            # Native held-state queries exclude conflicts with pre-existing human holds.
            if self._held(key=key):
                raise InputInterrupted("key is already held outside this lease")
            if self._native():
                self.gui.keyDown(key, target=frame.foreground_window)
            elif getattr(self.gui, "__name__", "") == "pyautogui" and sys.platform == "linux":
                from Xlib import X
                from Xlib.ext.xtest import fake_input

                code = self._x11_keycode(key)
                fake_input(self.gui.platformModule._display, X.KeyPress, code)
                self.gui.platformModule._display.sync()
                self.x11_keys[key] = code
            else:
                self.gui.keyDown(KEY_ALIASES.get(key, key), _pause=False)
            self.keys.add(key)
            self.owned.append(("key", key))
            if acknowledged is not None:
                acknowledged()
            self._sync()

    def _button_down(self, button, frame, acknowledged=None):
        with self.lock:
            if button in self.buttons:
                raise InputInterrupted("button already owned")
            if self._held(button=button):
                raise InputInterrupted("button is already held outside this lease")
            if self._native():
                self.gui.mouseDown(button, target=frame.foreground_window)
            elif getattr(self.gui, "__name__", "") == "pyautogui" and sys.platform == "linux":
                from .x11_input_state import button_event

                code = self._x11_state().button_code(button)
                button_event(self.gui.platformModule._display, code, True)
                self.x11_buttons[button] = code
            else:
                self.gui.mouseDown(button=button, _pause=False)
            self.buttons.add(button)
            self.owned.append(("button", button))
            if acknowledged is not None:
                acknowledged()
            self._sync()

    def _up(self, kind, value):
        with self.lock:
            pool = self.keys if kind == "key" else self.buttons
            if value not in pool or (kind, value) not in self.owned:
                raise InputInterrupted("release refused: input belongs to another owner")
            if kind == "key":
                if self._native():
                    self.gui.keyUp(value)
                elif getattr(self.gui, "__name__", "") == "pyautogui" and sys.platform == "linux":
                    from Xlib import X
                    from Xlib.ext.xtest import fake_input

                    # Recovery owns the acknowledged physical code, regardless
                    # of the current logical layout or mapping caches.
                    fake_input(self.gui.platformModule._display, X.KeyRelease, self.x11_keys[value])
                    self.gui.platformModule._display.sync()
                    del self.x11_keys[value]
                else:
                    self.gui.keyUp(KEY_ALIASES.get(value, value), _pause=False)
            else:
                if self._native():
                    self.gui.mouseUp(button=value)
                elif getattr(self.gui, "__name__", "") == "pyautogui" and sys.platform == "linux":
                    from .x11_input_state import button_event

                    button_event(self.gui.platformModule._display, self.x11_buttons[value], False)
                    del self.x11_buttons[value]
                else:
                    self.gui.mouseUp(button=value, _pause=False)
            pool.discard(value)
            self.owned.remove((kind, value))
            self._sync()

    def release(self, only=None):
        with self.lock:
            previous = self.gui.FAILSAFE
            self.gui.FAILSAFE = False
            errors = []
            try:
                for kind, value in reversed(tuple(self.owned)):
                    if only is not None and (kind, value) not in only:
                        continue
                    try:
                        self._up(kind, value)
                    except Exception as exc:
                        errors.append(exc)
                if self._native():
                    try:
                        self.gui.release_text()
                    except Exception as exc:
                        errors.append(exc)
                if not self.owned and not self.active:
                    self.watch = None
                    self._sync()
            finally:
                self.gui.FAILSAFE = previous
            if errors:
                raise errors[0]

    def _move(self, point, frame):
        width, height = frame.logical_size or frame.image.size
        x = frame.origin[0] + min(width - 1, int(point[0] * width))
        y = frame.origin[1] + min(height - 1, int(point[1] * height))
        if self._native():
            self.gui.moveTo(x, y)
        else:
            self.gui.moveTo(x, y, _pause=False)

    def execute(
        self,
        command,
        frame,
        cancelled,
        context_guard=None,
        deadline=None,
        context=None,
        after_input_guard=None,
    ):
        if self.x11_state is not None and os.getpid() != self.x11_state.process:
            self.x11_state._binding()
        with self.execution_lock:
            self.delivery = None
            try:
                return self._execute_locked(
                    command, frame, cancelled, context_guard, deadline, context, after_input_guard
                )
            except Exception as error:
                if self.delivery is not None:
                    raise InputDispatchError(str(error), self.delivery) from error
                raise

    def _execute_locked(
        self,
        command,
        frame,
        cancelled,
        context_guard=None,
        deadline=None,
        context=None,
        after_input_guard=None,
    ):
        from .schema import ActionResult, InputDelivery

        command = INPUT_ADAPTER.validate_python(command)
        if isinstance(command, (KeyInput, PointerInput)) and command.phase == "up":
            # Recovery releases are tied to ownership, never to the target's
            # current focus, text or IME state.
            if self.watch is not None and self.watch[0] is not cancelled:
                return ActionResult(ok=False, reason="held input belongs to another lease")
            try:
                self._up(
                    "key" if isinstance(command, KeyInput) else "button",
                    command.key if isinstance(command, KeyInput) else command.button,
                )
                self.release(only=())
                return ActionResult(ok=True)
            except InputInterrupted as exc:
                return ActionResult(ok=False, reason=str(exc))
        if isinstance(command, KeyInput) and command.physical_code is not None:
            return ActionResult(ok=False, reason="physical key code injection unavailable")
        hold = (
            isinstance(command, KeyInput)
            and command.phase == "down"
            or (isinstance(command, PointerInput) and command.phase == "down")
        )
        if hold and deadline is None:
            return ActionResult(ok=False, reason="held input requires a bounded deadline")
        exact_text_control = False
        if context is not None:
            context = InputContext.model_validate(context)
            if isinstance(command, (KeyInput, ChordInput)) and not (
                isinstance(command, KeyInput) and command.key == "escape"
            ):
                text_control = context.text_focus is True and (
                    (
                        context.text_control == "select_all"
                        and isinstance(command, ChordInput)
                        and command.modifiers in {("ctrl",), ("command",)}
                        and command.key == "a"
                    )
                    or (
                        context.text_control == "submit"
                        and isinstance(command, KeyInput)
                        and command.key == "enter"
                        and command.phase == "tap"
                        and command.repeat == 1
                        and command.hold_seconds == 0
                    )
                )
                exact_text_control = text_control
                if context.ime_composing is not False or (
                    context.text_focus is not False and not text_control
                ):
                    return ActionResult(
                        ok=False, reason="shortcut requires known idle IME and no text focus"
                    )
            if isinstance(command, TextInput) and context.ime_composing is not False:
                return ActionResult(ok=False, reason="literal insertion requires known idle IME")
        if after_input_guard is not None and not (
            context is not None
            and context.ime_composing is False
            and context_guard is not None
            and (
                isinstance(command, ChordInput)
                or isinstance(command, GestureInput)
                and context.text_focus is False
                or (
                    isinstance(command, KeyInput)
                    and command.phase == "tap"
                    and command.repeat == 1
                    and command.hold_seconds == 0
                )
            )
        ):
            return ActionResult(
                ok=False, reason="post-input guard requires bounded trigger and known idle IME"
            )
        phase_guard = [context_guard]
        trigger_keys = (
            (*command.modifiers, command.key)
            if isinstance(command, ChordInput)
            else (command.key,)
            if isinstance(command, KeyInput)
            else None
        )
        execution_id = uuid.uuid4().hex if trigger_keys is not None else None

        def acknowledged():
            if trigger_keys is not None:
                self.delivery = InputDelivery(
                    execution_id=execution_id,
                    kind=command.kind,
                    keys=trigger_keys,
                    acknowledged_at_ns=time.monotonic_ns(),
                )
            if after_input_guard is not None:
                phase_guard[0] = after_input_guard

        def current_guard():
            # A watcher cannot observe the post-trigger state using the old guard
            # between successful native acknowledgement and this phase latch.
            with self.lock:
                callback = phase_guard[0]
                return callback() if callback is not None else None

        context_guard = current_guard
        deadline = deadline if deadline is not None else time.monotonic() + 3
        if not math.isfinite(deadline) or deadline - time.monotonic() > 30:
            return ActionResult(ok=False, reason="input deadline exceeds 30 seconds")
        self._check(cancelled, deadline, context_guard, frame)
        if after_input_guard is not None and self.owned:
            return ActionResult(
                ok=False, reason="post-input transition requires no held agent input"
            )
        if exact_text_control and self.owned:
            return ActionResult(ok=False, reason="exact text control requires no held agent input")
        if isinstance(command, TextInput) and self.owned:
            return ActionResult(ok=False, reason="literal insertion requires no held agent input")
        previous_owned = tuple(self.owned)
        if self.watch is not None and previous_owned:
            if self.watch[0] is not cancelled:
                return ActionResult(ok=False, reason="held input belongs to another lease")
            deadline = min(deadline, self.watch[1])
        self._arm(cancelled, deadline, context_guard, frame)
        self.active = True
        retain = False
        succeeded = False
        try:
            if isinstance(command, KeyInput):
                if command.phase == "up":
                    self._up("key", command.key)
                else:
                    for _ in range(command.repeat):
                        with self.lock:
                            self._check(cancelled, deadline, context_guard, frame)
                            self._key_down(command.key, frame, acknowledged)
                        if command.phase == "down":
                            retain = True
                            break
                        cancelled.wait(command.hold_seconds)
                        self._up("key", command.key)
            elif isinstance(command, ChordInput):
                for index, key in enumerate(trigger_keys):
                    with self.lock:
                        self._check(cancelled, deadline, context_guard, frame)
                        self._key_down(
                            key, frame, acknowledged if index == len(trigger_keys) - 1 else None
                        )
            elif isinstance(command, PointerInput):
                if command.point is not None:
                    self._move(command.point, frame)
                self._check(cancelled, deadline, context_guard, frame)
                if command.phase == "up":
                    self._up("button", command.button)
                elif command.phase in {"down", "click"}:
                    self._button_down(command.button, frame)
                    retain = command.phase == "down"
            elif isinstance(command, GestureInput):
                self._move(command.points[0], frame)
                for key in command.modifiers:
                    self._check(cancelled, deadline, context_guard, frame)
                    self._key_down(key, frame)
                with self.lock:
                    self._check(cancelled, deadline, context_guard, frame)
                    self._button_down(command.button, frame, acknowledged)
                for point in command.points[1:]:
                    self._check(cancelled, deadline, context_guard, frame)
                    self._move(point, frame)
                    cancelled.wait(command.duration / (len(command.points) - 1))
            elif isinstance(command, WheelInput):
                self._move(command.point, frame)
                self._check(cancelled, deadline, context_guard, frame)
                if getattr(self.gui, "__name__", "") == "pyautogui" and sys.platform == "linux":
                    button = (
                        (4 if command.amount > 0 else 5)
                        if command.axis == "vertical"
                        else (7 if command.amount > 0 else 6)
                    )
                    for _ in range(abs(command.amount)):
                        self._check(cancelled, deadline, context_guard, frame)
                        self._button_down(button, frame)
                        self._up("button", button)
                else:
                    name = "scroll" if command.axis == "vertical" else "hscroll"
                    function = getattr(self.gui, name, None)
                    if function is None:
                        return ActionResult(ok=False, reason="wheel axis unavailable")
                    if self._native():
                        function(command.amount, target=frame.foreground_window)
                    else:
                        function(command.amount)
            else:
                self._text(command, frame, cancelled, deadline, context_guard)
            self._check(cancelled, deadline, context_guard, frame)
            succeeded = True
            return ActionResult(ok=True, delivery=self.delivery)
        except InputInterrupted as exc:
            return ActionResult(ok=False, reason=str(exc), delivery=self.delivery)
        finally:
            self.active = False
            if not succeeded or cancelled.is_set():
                self.release()
            elif not retain:
                self.release(only=set(self.owned) - set(previous_owned))

    def _text(self, command, frame, cancelled, deadline, guard):
        if command.method == "unicode":
            if not hasattr(self.gui, "type_text"):
                raise InputInterrupted(
                    "exact native Unicode unavailable; select clipboard explicitly"
                )
            self.gui.type_text(
                command.text,
                cancelled,
                frame.foreground_window,
                before_input=lambda: self._check(cancelled, deadline, guard, frame),
            )
            return
        if getattr(self.gui, "__name__", "") == "pyautogui" and sys.platform == "linux":
            from .x11_clipboard import ClipboardTransferError, X11ClipboardTransfer

            transfer = None
            paste_attempted = False

            def close_transfer():
                if transfer is None:
                    return
                try:
                    if not paste_attempted and not transfer.closed:
                        self.release()
                        transfer.cancel_before_trigger(deadline=time.monotonic() + 0.5)
                finally:
                    transfer.close()

            try:
                transfer = X11ClipboardTransfer(
                    command.text,
                    self.gui.platformModule._display.get_display_name(),
                    deadline,
                    cancelled,
                    lambda: self._check(cancelled, deadline, guard, frame),
                )
                for key in ("ctrl", "v"):
                    self._check(cancelled, deadline, guard, frame)
                    if key == "v":
                        transfer.arm()
                        self._check(cancelled, deadline, guard, frame)
                        # A failed OS request can still have delivered input.
                        # Restoration is no longer authorized after this point.
                        paste_attempted = True
                    self._key_down(key, frame)
                self.release()
                transfer.wait_consumed()
            except (ClipboardTransferError, InputInterrupted) as exc:
                recovery_error = None
                try:
                    close_transfer()
                except ClipboardTransferError as cleanup:
                    recovery_error = str(cleanup)
                unresolved = transfer is not None and transfer.unresolved
                reason = str(exc)
                if recovery_error is not None:
                    reason += f"; pre-paste recovery failed: {recovery_error}"
                if unresolved:
                    reason += "; clipboard transfer unacknowledged"
                    reason += "; pending clipboard ownership unresolved"
                raise InputInterrupted(reason) from exc
            finally:
                close_transfer()
            return
        import pyperclip

        previous = pyperclip.paste()
        try:
            pyperclip.copy(command.text)
            for key in ("command" if sys.platform == "darwin" else "ctrl", "v"):
                self._check(cancelled, deadline, guard, frame)
                self._key_down(key, frame)
            self.release()
            cancelled.wait(0.1)
        finally:
            # Do not overwrite a clipboard edit made concurrently by the user.
            if pyperclip.paste() == command.text:
                pyperclip.copy(previous)


def _guardian_main():
    """Pipe reader thread leaves the guardian free to handle a stalled parent."""
    if sys.platform == "win32":
        from .windows_input import Input, KeyboardInput, WindowsInput

        gui = WindowsInput()
    else:
        import pyautogui as gui
    gui.FAILSAFE = False
    print("ready", flush=True)
    updates = queue.Queue()

    def read():
        for line in sys.stdin:
            updates.put(json.loads(line))
        updates.put(None)

    threading.Thread(target=read, daemon=True).start()
    owned, deadline, native_keys, unicode_units, x11_keys, x11_buttons = [], None, {}, [], {}, {}
    while True:
        try:
            message = updates.get(timeout=0.01)
        except queue.Empty:
            message = {}
        if message is not None and message:
            owned, deadline = [tuple(item) for item in message["owned"]], message["deadline"]
            native_keys = message.get("native_keys", {})
            unicode_units = message.get("unicode_units", [])
            x11_keys = message.get("x11_keys", {})
            x11_buttons = message.get("x11_buttons", {})
        expired = deadline is not None and time.monotonic() >= deadline
        if message is None or expired:
            if sys.platform == "win32":
                owned = [
                    *owned,
                    *[("key", key) for key in native_keys if ("key", key) not in owned],
                ]
            elif sys.platform == "linux":
                owned = [
                    *owned,
                    *[("key", key) for key in x11_keys if ("key", key) not in owned],
                    *[
                        ("button", int(value) if value.isdigit() else value)
                        for value in x11_buttons
                        if ("button", int(value) if value.isdigit() else value) not in owned
                    ],
                ]
            for kind, value in reversed(owned):
                try:
                    if kind == "key":
                        # Guardian did not inject the down; native ownership is local.
                        if sys.platform == "win32":
                            vk, scan, flags = native_keys[value]
                            gui._send(
                                Input(type=1, keyboard=KeyboardInput(vk, scan, flags | 2, 0, 0))
                            )
                            # A later EOF must not release a new owner's hold
                            # using an acknowledgement already discharged here.
                            native_keys.pop(value)
                        elif sys.platform == "linux":
                            from Xlib import X
                            from Xlib.ext.xtest import fake_input

                            fake_input(gui.platformModule._display, X.KeyRelease, x11_keys[value])
                            gui.platformModule._display.sync()
                        else:
                            gui.keyUp(KEY_ALIASES.get(value, value), _pause=False)
                    else:
                        if sys.platform == "linux":
                            from .x11_input_state import button_event

                            button_event(
                                gui.platformModule._display, x11_buttons[str(value)], False
                            )
                        else:
                            gui.mouseUp(button=value)
                except Exception:
                    pass  # Recovery is best effort under the same OS permissions.
            if sys.platform == "win32":
                for unit in tuple(unicode_units):
                    try:
                        gui._send(Input(type=1, keyboard=KeyboardInput(0, unit, 6, 0, 0)))
                        unicode_units.remove(unit)
                    except Exception:
                        pass
            owned, deadline, x11_keys, x11_buttons = [], None, {}, {}
            if message is None:
                return


if __name__ == "__main__" and sys.argv[1:] == ["--guardian"]:
    _guardian_main()

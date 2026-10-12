"""Six finite, guarded local operations, separate from instruction-only Skills.

The observer supplies trusted local evidence. Requests cannot supply state or
arbitrary executable steps. Every changing operation needs observed key bindings
and final application readback; successful input delivery alone never suffices.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from .input_ir import ChordInput, GestureInput, KeyInput, TextInput
from .schema import ActionResult, StrictModel
from .state import BlenderSceneUnits, CompiledState, StateUnavailable


class MenuAssess(StrictModel):
    family: Literal["menu_assess"] = "menu_assess"
    menu: Literal["File", "Edit", "Render", "Window", "Help"]


class CommandSearch(StrictModel):
    family: Literal["command_search"] = "command_search"
    command: Literal["object.shade_smooth", "object.shade_flat"]
    target_id: str = Field(min_length=1, max_length=200)
    keymap_version: str = Field(min_length=1, max_length=200)


class NumericTransform(StrictModel):
    family: Literal["numeric_transform"] = "numeric_transform"
    target_id: str = Field(min_length=1, max_length=200)
    operation: Literal["translate", "rotate", "scale"]
    axis: Literal["X", "Y", "Z"]
    space: Literal["GLOBAL", "LOCAL"]
    unit: Literal["NONE", "METERS", "CENTIMETERS", "DEGREES", "RADIANS"]
    amount: float = Field(ge=-100000, le=100000)
    keymap_version: str = Field(min_length=1, max_length=200)
    commit: bool = True
    tolerance: float = Field(default=1e-5, gt=0, le=0.001)

    @model_validator(mode="after")
    def unit_compatible(self):
        if self.operation == "scale" and self.unit != "NONE":
            raise ValueError("scale requires unit NONE")
        if self.operation == "rotate" and self.unit not in {"DEGREES", "RADIANS"}:
            raise ValueError("rotation requires an explicit angular unit")
        if self.operation == "translate" and self.unit not in {"NONE", "METERS", "CENTIMETERS"}:
            raise ValueError("translation requires a distance unit")
        return self


class PropertyEdit(StrictModel):
    family: Literal["property_edit"] = "property_edit"
    target_id: str = Field(min_length=1, max_length=200)
    field: Literal["location_x", "location_y", "location_z", "scale_x", "scale_y", "scale_z"]
    value: float = Field(ge=-100000, le=100000)
    keymap_version: str = Field(min_length=1, max_length=200)
    tolerance: float = Field(default=1e-5, gt=0, le=0.001)

    @model_validator(mode="after")
    def field_range(self):
        if self.field.startswith("scale_") and not 0.000001 <= self.value <= 10000:
            raise ValueError("scale property must be in [0.000001, 10000]")
        return self


class ViewportGesture(StrictModel):
    family: Literal["viewport_gesture"] = "viewport_gesture"
    gesture: Literal["orbit", "pan"]
    points: tuple[tuple[float, float], tuple[float, float]]
    surface: tuple[float, float, float, float]
    duration: float = Field(default=0.15, ge=0.05, le=0.25)
    keymap_version: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def bounded(self):
        x1, y1, x2, y2 = self.surface
        if not 0 <= x1 < x2 <= 1 or not 0 <= y1 < y2 <= 1:
            raise ValueError("viewport surface must be normalized and have positive area")
        if any(not x1 <= x <= x2 or not y1 <= y <= y2 for x, y in self.points):
            raise ValueError("viewport gesture must stay inside its observed editor surface")
        if math.dist(*self.points) > 0.25:
            raise ValueError("viewport gesture exceeds the bounded movement limit")
        return self


class ModalCancel(StrictModel):
    family: Literal["modal_cancel"] = "modal_cancel"
    modal_id: str = Field(min_length=1, max_length=200)


OperationRequest = Annotated[
    MenuAssess | CommandSearch | NumericTransform | PropertyEdit | ViewportGesture | ModalCancel,
    Field(discriminator="family"),
]
_REQUEST_ADAPTER = TypeAdapter(OperationRequest)


def parse_operation_request(value: dict) -> OperationRequest:
    return _REQUEST_ADAPTER.validate_python(value)


class OperationReport(StrictModel):
    family: str
    status: Literal["SUCCEEDED", "BLOCKED", "FAILED", "ABORTED"]
    reason: str
    assessment: Literal["OPEN", "ABSENT", "WRONG_MENU", "AMBIGUOUS", "UNKNOWN"] | None = None
    transitions: tuple[str, ...] = ()
    state_version: int | None = None
    access_level: str | None = None
    owned_modal_id: str | None = None
    geometry_invalidated: bool = False
    input_count: int = Field(default=0, ge=0)


_CONTEXT_FACTS = (
    "application",
    "window",
    "foreground",
    "editor",
    "mode",
    "keymap_version",
    "selection",
    "selection_identities",
    "ime_composing",
    "text_focus",
)
_BASE_FACTS = _CONTEXT_FACTS + (
    "loading",
    "popup",
    "modal",
    "owned_inputs",
    "target_geometry",
    "keymap",
)
_CANCEL_FACTS = _CONTEXT_FACTS + (
    "loading",
    "popup",
    "modal",
    "space",
    "unit",
    "keymap",
    "transform_values",
    "transform_context",
)

_REGISTRY = (
    ("menu_assess", "Read-only menu assessment", (), ("menus",), "No input"),
    (
        "command_search",
        "Authorized command search",
        ("object.shade_smooth", "object.shade_flat"),
        ("keymap", "selection", "mode", "command_result", "properties"),
        "Known owned modal only",
    ),
    (
        "numeric_transform",
        "Numeric transform with preview and readback",
        (),
        (
            "selection",
            "space",
            "unit",
            "transform_values",
            "transform_preview",
            "transform_context",
            "modal",
        ),
        "Cancel only the observed modal entered by this runner",
    ),
    (
        "property_edit",
        "Exact focused property edit",
        (),
        ("selection", "focused_property", "text_focus", "properties"),
        "No blind Escape",
    ),
    (
        "viewport_gesture",
        "Bounded viewport orbit or pan",
        (),
        ("editor", "keymap", "view_revision", "owned_inputs"),
        "Release owned inputs; reacquire geometry",
    ),
    (
        "modal_cancel",
        "Cancel a known owned modal",
        (),
        ("modal", "transform_values"),
        "Refuse unknown or externally replaced modal",
    ),
)


def operation_registry() -> tuple[dict, ...]:
    models = (
        MenuAssess,
        CommandSearch,
        NumericTransform,
        PropertyEdit,
        ViewportGesture,
        ModalCancel,
    )
    return tuple(
        {
            "family": family,
            "description": description,
            "authorized_commands": commands,
            "requires": tuple(
                dict.fromkeys(
                    (
                        ()
                        if family == "menu_assess"
                        else _CANCEL_FACTS
                        if family == "modal_cancel"
                        else _BASE_FACTS
                    )
                    + requires
                )
            ),
            "requires_owned_modal": (
                {"scope": "same_session", "identity": "exact_current_modal_id"}
                if family == "modal_cancel"
                else None
            ),
            **(
                {
                    "requires_by_field": {
                        field: ("scene_units",)
                        for field in ("location_x", "location_y", "location_z")
                    },
                    "value_semantics": {
                        "location_x/location_y/location_z": "Raw Object.location coordinates in "
                        "Blender units; observed scene scale determines explicit meter input",
                        "scale_x/scale_y/scale_z": "Dimensionless Object.scale factors",
                    },
                }
                if family == "property_edit"
                else {}
            ),
            "recovery": recovery,
            "execution": "guarded_local_finite_state_machine",
            "schema": model.model_json_schema(),
        }
        for (family, description, commands, requires, recovery), model in zip(
            _REGISTRY, models, strict=True
        )
    )


class OperationBlocked(ValueError):
    pass


def selection_identity_anchor(state: CompiledState) -> dict[str, str]:
    """Require an exact observed identity for every uniquely selected name."""
    selection = state.require("selection")
    identities = state.require("selection_identities")
    if (
        not isinstance(selection, list)
        or any(not isinstance(name, str) or not name for name in selection)
        or len(set(selection)) != len(selection)
        or not isinstance(identities, dict)
        or set(identities) != set(selection)
        or any(
            not isinstance(identity, str) or not 1 <= len(identity) <= 256 or "\x00" in identity
            for identity in identities.values()
        )
        or len(set(identities.values())) != len(identities)
    ):
        raise OperationBlocked("selection identities must exactly identify unique selected objects")
    return dict(identities)


class OperationRunner:
    def __init__(
        self,
        observer: Callable[[], CompiledState],
        executor: Callable,
        text_method: Literal["unicode", "clipboard"] = "clipboard",
    ):
        self.observer = observer
        self.executor = executor
        self.text_method = text_method
        self._owned_modal: dict | None = None
        self._invalidated_version = 0
        self._lock = threading.Lock()

    def owns_modal(self, modal_id: str | None = None) -> bool:
        with self._lock:
            return bool(
                self._owned_modal and (modal_id is None or self._owned_modal["id"] == modal_id)
            )

    def run(self, request: OperationRequest, cancelled: threading.Event) -> OperationReport:
        request = _REQUEST_ADAPTER.validate_python(request)
        if not self._lock.acquire(blocking=False):
            return OperationReport(family=request.family, status="BLOCKED", reason="operation busy")
        self._steps: list[str] = []
        self._state: CompiledState | None = None
        self._sent = False
        self._input_count = 0
        self._last_acknowledged_command = None
        self._view_input_sent = False
        self._selection_anchor: dict[str, str] | None = None
        try:
            self._state = self.observer()
            if cancelled.is_set():
                raise InterruptedError("operation aborted before input")
            if isinstance(request, MenuAssess):
                return self._menu(request)
            if isinstance(request, ModalCancel):
                return self._cancel(request, cancelled)
            self._base(request)
            if isinstance(request, CommandSearch):
                self._command(request, cancelled)
            elif isinstance(request, NumericTransform):
                self._transform(request, cancelled)
            elif isinstance(request, PropertyEdit):
                self._property(request, cancelled)
            elif isinstance(request, ViewportGesture):
                self._viewport(request, cancelled)
            return self._report(request, "SUCCEEDED", "application readback verified")
        except InterruptedError as exc:
            return self._report(request, "ABORTED", str(exc))
        except (
            OperationBlocked,
            StateUnavailable,
            KeyError,
            TypeError,
            ValueError,
            RuntimeError,
        ) as exc:
            return self._report(request, "FAILED" if self._sent else "BLOCKED", str(exc))
        finally:
            self._lock.release()

    def _report(self, request, status, reason, **extra):
        self._reconcile_closed_modal()
        state = self._state
        return OperationReport(
            family=request.family,
            status=status,
            reason=reason,
            transitions=tuple(self._steps),
            state_version=state.version if state else None,
            access_level=state.access_level if state else None,
            owned_modal_id=self._owned_modal["id"] if self._owned_modal else None,
            geometry_invalidated=self._view_input_sent,
            **extra,
            input_count=self._input_count,
        )

    def _reconcile_closed_modal(self):
        owned = self._owned_modal
        if not owned:
            return
        try:
            # Closure is read-only window evidence. It can release obsolete
            # recovery authority even when the former target was replaced.
            self._state = self.observer()
            for name in ("application", "window"):
                self._expect(name, owned["anchor"][name])
            self._expect("modal", None)
        except Exception:
            # Unavailable or differently bound evidence cannot establish that
            # the original window's modal closed. Preserve the original result.
            return
        self._owned_modal = None
        self._steps.append("owned_modal_closed_observed")
        try:
            if selection_identity_anchor(self._state) != owned["anchor"]["selection_identities"]:
                return
            unchanged = self._fact("transform_values") == owned["before"]
        except (StateUnavailable, OperationBlocked):
            return
        self._steps.append(
            "unchanged_readback_observed" if unchanged else "changed_readback_observed"
        )

    def _fact(self, name):
        return self._state.require(name)

    def _expect(self, name, expected):
        if self._fact(name) != expected:
            raise OperationBlocked(f"{name} does not match required {expected!r}")

    def _base(self, request):
        for name, expected in (
            ("application", "Blender"),
            ("foreground", True),
            ("mode", "OBJECT"),
            ("ime_composing", False),
            ("popup", False),
            ("loading", False),
        ):
            self._expect(name, expected)
        editor = self._fact("editor")
        if editor not in (
            {"VIEW_3D", "PROPERTIES"} if isinstance(request, PropertyEdit) else {"VIEW_3D"}
        ):
            raise OperationBlocked("editor does not match operation family")
        self._fact("window")
        self._expect("modal", None)
        self._expect("owned_inputs", [])
        self._expect("keymap_version", request.keymap_version)
        if self._state.fact("target_geometry").state_version <= self._invalidated_version:
            raise OperationBlocked("viewport changed; reacquire target geometry before editing")
        self._fact("target_geometry")
        if hasattr(request, "target_id"):
            self._expect("selection", [request.target_id])
        self._selection_anchor = selection_identity_anchor(self._state)
        if not isinstance(request, PropertyEdit):
            self._expect("text_focus", False)
        self._expected_popup = False
        self._anchor = {name: self._fact(name) for name in _CONTEXT_FACTS}
        # Version labels do not substitute for the observed binding content.
        self._anchor["keymap"] = self._fact("keymap")
        if isinstance(request, NumericTransform):
            self._anchor.update({name: self._fact(name) for name in ("space", "unit")})
        if isinstance(request, PropertyEdit):
            self._anchor["focused_property"] = self._fact("focused_property")
            if request.field.startswith("location_"):
                self._anchor["scene_units"] = self._fact("scene_units")
        self._steps.append("requires_verified")

    def _refresh(self):
        self._state = self.observer()
        if (
            self._selection_anchor is not None
            and selection_identity_anchor(self._state) != self._selection_anchor
        ):
            raise OperationBlocked("selection identities changed during operation")
        return self._state

    def _send(self, command, cancelled):
        if cancelled.is_set():
            raise InterruptedError("operation aborted")
        self._refresh()
        for name, value in self._anchor.items():
            self._expect(name, value)
        self._expect("loading", False)
        self._expect("popup", self._expected_popup)
        if self._owned_modal:
            self._expect(
                "modal", {"id": self._owned_modal["id"], "name": self._owned_modal["name"]}
            )
        else:
            self._expect("modal", None)
        # A failed native gesture may already have moved the view. Invalidate
        # at dispatch, including exceptions/cancellation after partial input.
        gesture = isinstance(command, GestureInput)
        if gesture:
            self._view_input_sent = True
            self._invalidated_version = self._state.version
        dispatch_started_ns = time.monotonic_ns()
        try:
            result: ActionResult = self.executor(command, self._state, cancelled)
        finally:
            if gesture:
                self._state = self._state.invalidate_geometry()
        self._sent = True
        expected_keys = (
            (command.key,)
            if isinstance(command, KeyInput)
            else (*command.modifiers, command.key)
            if isinstance(command, ChordInput)
            else None
        )
        delivery = result.delivery
        acknowledged = (
            delivery is not None
            and expected_keys is not None
            and delivery.kind == command.kind
            and delivery.keys == expected_keys
            and dispatch_started_ns <= delivery.acknowledged_at_ns <= time.monotonic_ns()
        )
        if result.ok or acknowledged:
            self._input_count += 1
            self._last_acknowledged_command = command
        if cancelled.is_set():
            raise InterruptedError("operation aborted during input")
        if not result.ok:
            raise OperationBlocked(f"input refused: {result.reason}")

    def _binding(self, name):
        keymap = self._fact("keymap")
        keys = keymap.get(name) if isinstance(keymap, dict) else None
        if not isinstance(keys, list) or not keys or not all(isinstance(k, str) for k in keys):
            raise OperationBlocked(f"observed keymap lacks {name}")
        return (
            KeyInput(key=keys[0])
            if len(keys) == 1
            else ChordInput(modifiers=tuple(keys[:-1]), key=keys[-1])
        )

    def _menu(self, request):
        try:
            menus = self._fact("menus")
            if not isinstance(menus, list) or any(
                not isinstance(m, dict)
                or not isinstance(m.get("open"), bool)
                or not isinstance(m.get("name"), str)
                or not isinstance(m.get("id"), str)
                for m in menus
            ):
                raise StateUnavailable(
                    "menu evidence must include observed id, name and open state"
                )
            opened = [m for m in menus if m["open"]]
            matching = [m for m in opened if m["name"] == request.menu]
            assessment = (
                "AMBIGUOUS"
                if len(matching) > 1
                else (
                    "OPEN"
                    if len(matching) == 1 and len(opened) == 1
                    else (
                        "WRONG_MENU"
                        if opened and not matching
                        else ("AMBIGUOUS" if opened else "ABSENT")
                    )
                )
            )
            return self._report(
                request, "SUCCEEDED", "read-only menu evidence assessed", assessment=assessment
            )
        except StateUnavailable as exc:
            return self._report(request, "BLOCKED", str(exc), assessment="UNKNOWN")

    def _command(self, request, cancelled):
        title, expected = {
            "object.shade_smooth": ("Shade Smooth", "SMOOTH"),
            "object.shade_flat": ("Shade Flat", "FLAT"),
        }[request.command]
        search, commit = self._binding("search"), self._binding("commit")
        self._send(search, cancelled)
        self._refresh()
        self._expect("popup", "COMMAND_SEARCH")
        self._expected_popup = "COMMAND_SEARCH"
        self._anchor["text_focus"] = self._fact("text_focus")
        # Search is a native popup, not a Python console; only fixed registered
        # command labels can enter it.
        self._send(TextInput(text=title, method=self.text_method), cancelled)
        self._send(commit, cancelled)
        self._refresh()
        self._expect("popup", False)
        self._expect("modal", None)
        self._expect("command_result", request.command)
        if self._fact("properties")[request.target_id]["shading"] != expected:
            raise OperationBlocked("command result did not match target property readback")
        self._steps.extend(("registered_command_selected", "readback_verified"))

    def _transform(self, request, cancelled):
        self._expect("space", request.space)
        units = self._fact("unit")
        if not isinstance(units, dict) or units.get(request.operation) != request.unit:
            raise OperationBlocked("observed operation unit differs from requested unit")
        before_values = self._fact("transform_values")
        self._complete_transform(before_values)
        self._transform_frame(request, before_values)
        self._anchor["transform_context"] = self._fact("transform_context")
        self._anchor["transform_values"] = before_values
        before = before_values[request.target_id][request.operation][request.axis]
        expected = (
            before * request.amount if request.operation == "scale" else before + request.amount
        )
        enter = self._binding(request.operation)
        axis = self._binding("axis_" + request.axis.lower())
        commit, cancel = self._binding("commit"), self._binding("cancel")
        entered_normally = False
        try:
            self._send(enter, cancelled)
            entered_normally = True
        finally:
            # Entry can already preview a mouse delta. It must not redefine the
            # baseline, and that owned effect is not a context mismatch.
            self._anchor.pop("transform_values", None)
            # Cancellation can arrive immediately after the acknowledged key
            # that opens a modal. Reconcile read-only before returning abort so
            # the same session retains its narrowly verified cleanup authority.
            if self._last_acknowledged_command is enter:
                try:
                    self._claim_transform_modal(request, before_values, cancel)
                except Exception:
                    if entered_normally:
                        raise
        self._send(axis, cancelled)
        # Units are verified input/readback state, not keyboard suffixes. In
        # Blender, letters in a unit suffix can switch the active transform
        # (for example the "g" in "deg"). Never mix shortcuts into a number.
        self._send(
            TextInput(text=repr(request.amount), method=self.text_method),
            cancelled,
        )
        self._refresh()
        preview = self._fact("transform_preview")
        path = (request.target_id, request.operation, request.axis)
        if not self._readback_matches(preview, before_values, path, expected, request.tolerance):
            raise OperationBlocked("numeric preview differs from intended transform")
        self._steps.append("preview_verified")
        if request.commit:
            self._anchor["transform_preview"] = preview
        self._send(commit if request.commit else cancel, cancelled)
        self._anchor.pop("transform_preview", None)
        self._refresh()
        self._expect("modal", None)
        # A closed modal cannot be cancelled, even when final values reveal a
        # failed effect. Do not retain a recovery authority for that old ID.
        self._owned_modal = None
        if not self._readback_matches(
            self._fact("transform_values"),
            before_values,
            path,
            expected if request.commit else before,
            request.tolerance,
        ):
            raise OperationBlocked("final numeric readback differs from intended result")
        self._steps.extend(("committed" if request.commit else "cancelled", "readback_verified"))

    def _claim_transform_modal(self, request, before_values, cancel):
        self._refresh()
        for name, value in self._anchor.items():
            self._expect(name, value)
        self._expect("loading", False)
        self._expect("popup", False)
        self._expect("owned_inputs", [])
        modal = self._fact("modal")
        if (
            not isinstance(modal, dict)
            or modal.get("name") != request.operation
            or not modal.get("id")
        ):
            raise OperationBlocked("entered transform modal was not observed")
        self._owned_modal = {
            "id": modal["id"],
            "name": modal["name"],
            "before": before_values,
            "anchor": dict(self._anchor),
            "cancel": cancel,
        }
        self._steps.append("owned_modal_entered")

    @staticmethod
    def _complete_transform(values):
        """A partial vector cannot verify unchanged axes or transform channels."""
        if not isinstance(values, dict) or not values:
            raise OperationBlocked("complete numeric transform readback is unavailable")
        for transform in values.values():
            if not isinstance(transform, dict) or set(transform) != {
                "translate",
                "rotate",
                "scale",
            }:
                raise OperationBlocked("complete numeric transform readback is unavailable")
            for vector in transform.values():
                if (
                    not isinstance(vector, dict)
                    or set(vector) != set("XYZ")
                    or any(
                        isinstance(v, bool)
                        or not isinstance(v, (int, float))
                        or not math.isfinite(v)
                        for v in vector.values()
                    )
                ):
                    raise OperationBlocked("complete numeric transform readback is unavailable")

    @staticmethod
    def _readback_matches(actual, before, intended_path, intended, tolerance):
        """Verify the edited scalar and every other observed value and identity."""

        def matches(value, original, path=()):
            if isinstance(original, dict):
                return (
                    isinstance(value, dict)
                    and value.keys() == original.keys()
                    and all(matches(value[k], v, (*path, k)) for k, v in original.items())
                )
            if isinstance(original, list):
                return (
                    isinstance(value, list)
                    and len(value) == len(original)
                    and all(
                        matches(v, o, (*path, i))
                        for i, (v, o) in enumerate(zip(value, original, strict=True))
                    )
                )
            expected = intended if path == intended_path else original
            if type(expected) in (bool, str, type(None)):
                return type(value) is type(expected) and value == expected
            return (
                not isinstance(value, bool)
                and not isinstance(expected, bool)
                and isinstance(value, (int, float))
                and isinstance(expected, (int, float))
                and math.isfinite(value)
                and math.isfinite(expected)
                and math.isclose(value, expected, rel_tol=0, abs_tol=tolerance)
            )

        return matches(actual, before)

    def _transform_frame(self, request, values):
        context = self._fact("transform_context")[request.target_id]
        if (
            context.get("parent", "unknown") is not None
            or context.get("delta_identity") is not True
            or context.get("pivot") not in {"MEDIAN_POINT", "INDIVIDUAL_ORIGINS"}
        ):
            raise OperationBlocked(
                "scalar transform requires parentless target, identity delta and object pivot"
            )
        angles = values[request.target_id]["rotate"]
        aligned = all(abs(angles[a]) <= request.tolerance for a in "XYZ")
        if (
            (request.operation == "scale" and request.space == "GLOBAL")
            or (request.operation == "translate" and request.space == "LOCAL")
        ) and not aligned:
            raise OperationBlocked(
                "scalar readback cannot verify this rotated transform coordinate frame"
            )
        if request.operation == "rotate":
            if any(abs(angles[a]) > request.tolerance for a in "XYZ" if a != request.axis):
                raise OperationBlocked("scalar rotation requires alignment with the requested axis")
            limit = 180 if request.unit == "DEGREES" else math.pi
            if abs(angles[request.axis] + request.amount) >= limit:
                raise OperationBlocked("rotation crosses the scalar readback wrap boundary")
        if request.operation == "scale" and request.amount <= 0:
            raise OperationBlocked(
                "zero or negative scaling needs matrix readback; scalar path refuses it"
            )

    def _property(self, request, cancelled):
        self._expect("text_focus", True)
        self._expect("focused_property", {"target_id": request.target_id, "field": request.field})
        before_values = self._fact("properties")
        before = before_values[request.target_id][request.field]
        if isinstance(before, bool) or not isinstance(before, (int, float)):
            raise OperationBlocked("exact property readback is unavailable")
        literal = repr(request.value)
        if request.field.startswith("location_"):
            try:
                units = BlenderSceneUnits.model_validate(self._fact("scene_units"))
            except ValueError as exc:
                raise OperationBlocked("complete scene length conversion is unavailable") from exc
            if units.system != "NONE":
                meters = request.value * units.scale_length
                if not math.isfinite(meters) or (request.value != 0 and meters == 0):
                    raise OperationBlocked("scene length conversion exceeds numeric range")
                literal = repr(meters) + "m"
        select, commit = self._binding("select_all"), self._binding("commit")
        self._send(select, cancelled)
        self._send(TextInput(text=literal, method=self.text_method), cancelled)
        self._send(commit, cancelled)
        self._refresh()
        if request.field.startswith("location_"):
            self._expect("scene_units", self._anchor["scene_units"])
        if not self._readback_matches(
            self._fact("properties"),
            before_values,
            (request.target_id, request.field),
            request.value,
            request.tolerance,
        ):
            raise OperationBlocked("final literal property readback differs from requested value")
        self._steps.extend(("exact_field_verified", "readback_verified"))

    def _viewport(self, request, cancelled):
        geometry = self._fact("target_geometry")
        observed = geometry.get("editor_surface") if isinstance(geometry, dict) else None
        if not isinstance(observed, list) or len(observed) != 4:
            raise OperationBlocked("observed viewport editor geometry is unavailable")
        x1, y1, x2, y2 = request.surface
        if not (observed[0] <= x1 < x2 <= observed[2] and observed[1] <= y1 < y2 <= observed[3]):
            raise OperationBlocked("requested surface leaves the observed viewport editor")
        self._anchor["target_geometry"] = geometry
        keymap = self._fact("keymap")
        binding = keymap.get(request.gesture)
        if not isinstance(binding, dict) or binding.get("button") != "middle":
            raise OperationBlocked("observed viewport keymap lacks a middle-button binding")
        modifiers = binding.get("modifiers")
        if not isinstance(modifiers, list):
            raise OperationBlocked("observed viewport modifiers are unavailable")
        before = self._fact("view_revision")
        self._send(
            GestureInput(
                points=request.points,
                surface=request.surface,
                duration=request.duration,
                button="middle",
                modifiers=tuple(modifiers),
            ),
            cancelled,
        )
        self._refresh()
        if self._fact("view_revision") == before:
            raise OperationBlocked("viewport readback did not change")
        self._invalidated_version = self._state.version
        self._state = self._state.invalidate_geometry()
        self._steps.extend(("view_change_verified", "geometry_invalidated"))

    def _cancel(self, request, cancelled):
        owned = self._owned_modal
        if not owned or request.modal_id != owned["id"]:
            raise OperationBlocked("modal is not owned by this operation runner")
        self._expect("modal", {"id": owned["id"], "name": owned["name"]})
        self._anchor = owned["anchor"]
        self._selection_anchor = dict(self._anchor["selection_identities"])
        self._expected_popup = False
        self._send(owned["cancel"], cancelled)
        self._refresh()
        self._expect("modal", None)
        self._expect("transform_values", owned["before"])
        self._owned_modal = None
        self._steps.extend(("owned_modal_cancelled", "unchanged_readback_verified"))
        return self._report(request, "SUCCEEDED", "owned modal cancelled without commit")

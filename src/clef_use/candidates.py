import re
import sys

from .schema import ActionCandidate, BoundingBox, Contract, Observation, TextInput


def text_inputs(contract: Contract) -> list[TextInput]:
    if contract.text_inputs:
        return contract.text_inputs
    literals = re.findall(r'"([^"\r\n]{1,256})"', contract.goal)
    expressions = re.findall(r"\b\d+(?:\s*[+*/-]\s*\d+)+\b", contract.goal)
    numbers = re.findall(r"\b\d{1,10}\b", contract.goal) if not expressions else []
    return [TextInput(value=v) for v in dict.fromkeys(literals + expressions + numbers)][:8]


def effect_region(box):
    return BoundingBox(
        x1=max(0, box.x1 - 0.1),
        y1=max(0, box.y1 - 0.2),
        x2=min(1, box.x2 + 0.1),
        y2=min(1, box.y2 + 0.2),
    )


def pointer_allowed(pointer, observation):
    if pointer.reference != observation.frame.reference():
        return False
    frame = observation.frame
    width, height = frame.logical_size or frame.image.size
    if width <= 0 or height <= 0:
        return False
    positions = [frame.pointer_point(p) for p in pointer.points]
    area = pointer.surface
    if any(
        not (
            area.x1 <= (x - frame.origin[0]) / width <= area.x2
            and area.y1 <= (y - frame.origin[1]) / height <= area.y2
        )
        for x, y in positions
    ):
        return False
    bounds = observation.frame.foreground_bounds
    if bounds is not None:
        left, top, right, bottom = bounds
        if any(not (left <= x < right and top <= y < bottom) for x, y in positions):
            return False
    # Floor-to-device pixels and their coverage can cross normalized boundaries.
    # Padding the whole convex surface also covers every delivered stroke segment.
    pad_x, pad_y = 1 / width, 1 / height
    return not any(
        obj.sensitive
        and area.x1 - pad_x <= obj.bbox.x2
        and obj.bbox.x1 <= area.x2 + pad_x
        and area.y1 - pad_y <= obj.bbox.y2
        and obj.bbox.y1 <= area.y2 + pad_y
        for obj in observation.objects
    )


class CandidateBuilder:
    def __init__(self, limit: int = 48):
        self.limit = limit

    def build(self, observation: Observation, contract: Contract) -> tuple[ActionCandidate, ...]:
        candidates = []
        for pointer in contract.pointer_inputs:
            if len(candidates) < self.limit and pointer_allowed(pointer, observation):
                candidates.append(
                    ActionCandidate(
                        id=f"a{len(candidates)}",
                        operation=pointer.operation,
                        observation_id=observation.id,
                        description=(
                            f"{pointer.operation.title()} supplied pixel path: {pointer.label}"
                        ),
                        pointer=pointer,
                        expected_effect="content_change",
                        effect_roi=pointer.surface,
                    )
                )
        if contract.pointer_inputs:
            return tuple(candidates)
        objects = [
            obj
            for obj in observation.objects
            if not obj.sensitive
            and obj.visible is not False
            and obj.enabled is not False
            and obj.occluded is not True
        ]
        tokens = set(re.findall(r"\w+", contract.goal.lower()))
        objects.sort(
            key=lambda o: (
                -len(tokens & set(re.findall(r"\w+", o.label.lower()))),
                o.bbox.y1,
                o.bbox.x1,
                o.id,
            )
        )

        def add(operation, description, obj, value=None, effect="target_change"):
            if len(candidates) < self.limit:
                candidates.append(
                    ActionCandidate(
                        id=f"a{len(candidates)}",
                        operation=operation,
                        observation_id=observation.id,
                        target=obj.id,
                        description=description,
                        value=value,
                        expected_effect=effect,
                        effect_roi=effect_region(obj.bbox),
                    )
                )

        payloads = text_inputs(contract)
        reserve = min(len(payloads), 8)
        for obj in objects:
            if len(candidates) >= self.limit - reserve:
                break
            if "click" in obj.actions:
                add(
                    "click",
                    f"Click {obj.role}: {obj.label or 'unlabelled'}",
                    obj,
                    effect="content_change" if obj.label else "target_change",
                )
            if "focus" in obj.actions and obj.editable is not False:
                add("focus", f"Focus input: {obj.label}", obj, effect="focus_change")
            if "double_click" in obj.actions and re.search(
                r"double.click|launch|open", contract.goal, re.I
            ):
                add("double_click", f"Double click {obj.label}", obj)
            if "scroll" in obj.actions:
                for direction in ("up", "down"):
                    add("scroll", f"Scroll {direction}", obj, direction, "view_change")
        inputs = [obj for obj in objects if "type" in obj.actions and obj.editable is not False]
        for payload in payloads:
            targets = [
                obj
                for obj in inputs
                if payload.target_label is None
                or payload.target_label.casefold() in obj.label.casefold()
            ]
            if targets:
                obj = targets[0]
                add(
                    "type",
                    f"Enter exact supplied text into {obj.label}: {payload.value!r}",
                    obj,
                    payload.value,
                    "text_value",
                )
        # Focus is unknown for screenshot-only detections; do not synthesize generic
        # Enter/Backspace/SelectAll into an arbitrary active control.
        for obj in inputs:
            if obj.focused is not True:
                continue
            for key in ("enter", "tab", "backspace"):
                add("press", f"Press {key} in focused input", obj, key)
            modifier = "command" if sys.platform == "darwin" else "ctrl"
            add("hotkey", "Select text in focused field", obj, f"{modifier}+a")
        dialogs = [
            obj for obj in objects if re.search(r"dialog|modal|cancel|close", obj.label, re.I)
        ]
        if dialogs:
            add("press", "Dismiss visible dialog", dialogs[0], "escape", "view_change")
        return tuple(candidates)

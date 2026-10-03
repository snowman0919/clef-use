import re
import sys

from .schema import ActionCandidate, Contract, Observation, TextInput


def text_inputs(contract: Contract) -> list[TextInput]:
    if contract.text_inputs:
        return contract.text_inputs
    literals = re.findall(r'"([^"\r\n]{1,256})"', contract.goal)
    expressions = re.findall(r"\b\d+(?:\s*[+*/-]\s*\d+)+\b", contract.goal)
    numbers = re.findall(r"\b\d{1,10}\b", contract.goal) if not expressions else []
    return [TextInput(value=v) for v in dict.fromkeys(literals + expressions + numbers)][:8]


class CandidateBuilder:
    def __init__(self, limit: int = 48):
        self.limit = limit

    def build(self, observation: Observation, contract: Contract) -> tuple[ActionCandidate, ...]:
        candidates = []

        def add(operation, description, target=None, value=None):
            candidates.append(
                ActionCandidate(
                    id=f"a{len(candidates)}",
                    operation=operation,
                    observation_id=observation.id,
                    target=target,
                    description=description,
                    value=value,
                )
            )

        add("wait", "Wait briefly for the UI to settle")
        for key in ("escape", "enter", "tab", "backspace"):
            add("press", f"Press {key}", value=key)
        modifier = "command" if sys.platform == "darwin" else "ctrl"
        for key, description in (
            ("l", "Focus browser address bar"),
            ("a", "Select text in focused field"),
        ):
            add("hotkey", description, value=f"{modifier}+{key}")
        for direction in ("up", "down"):
            add("scroll", f"Scroll {direction}", value=direction)
        tokens = set(re.findall(r"\w+", contract.goal.lower()))
        objects = sorted(
            observation.objects,
            key=lambda o: (
                -len(tokens & set(re.findall(r"\w+", o.label.lower()))),
                o.bbox.y1,
                o.bbox.x1,
                o.id,
            ),
        )
        # Reserve part of the action budget for exact, planner-supplied text.
        payloads = text_inputs(contract)
        reserve = min(len(payloads), 8)
        for obj in objects:
            if obj.sensitive:
                continue
            if len(candidates) >= self.limit - reserve:
                break
            if "click" in obj.actions:
                add("click", f"Click {obj.role}: {obj.label or 'unlabelled'}", obj.id)
            if "focus" in obj.actions and len(candidates) < self.limit - reserve:
                add("focus", f"Focus input: {obj.label}", obj.id)
            if "double_click" in obj.actions and re.search(
                r"double.click|launch|open", contract.goal, re.I
            ):
                if len(candidates) < self.limit - reserve:
                    add("double_click", f"Double click {obj.label}", obj.id)
        for payload in payloads:
            targets = [
                o
                for o in objects
                if "type" in o.actions
                and not o.sensitive
                and (
                    payload.target_label is None
                    or payload.target_label.casefold() in o.label.casefold()
                )
            ]
            if targets:
                obj = targets[0]
                add(
                    "type",
                    f"Enter exact supplied text into {obj.label}: {payload.value!r}",
                    obj.id,
                    payload.value,
                )
            elif payload.target_label is None:
                add(
                    "type",
                    f"Enter exact supplied text into the focused field: {payload.value!r}",
                    value=payload.value,
                )
            if len(candidates) >= self.limit:
                break
        return tuple(candidates[: self.limit])

import hashlib
import json
import re

from .schema import BoundingBox, UIObject


def normalize_omni(raw: list[dict]) -> tuple[UIObject, ...]:
    objects, seen = [], set()
    for item in raw:
        coords = item["bbox"]
        box = BoundingBox.model_validate(dict(zip(("x1", "y1", "x2", "y2"), coords, strict=True)))
        label = str(item.get("content") or "")[:300]
        role = item.get("type", "unknown")
        if role not in {"text", "icon", "input", "button", "unknown"}:
            role = "unknown"
        sensitive = bool(re.search(r"password|passcode|secret|otp|비밀번호", label, re.I))
        actions = set()
        if item.get("interactivity", False):
            actions.update(("click", "double_click"))
            if role == "input" or re.search(r"input|field|textbox|search|address", label, re.I):
                actions.update(("focus", "type"))
            if re.search(r"scrollbar|scroll bar", label, re.I):
                actions.add("scroll")
        confidence = item.get("confidence")
        confidence = (float(confidence) or 0.0) if confidence is not None else None
        source = str(item.get("source", "vision"))
        # Deduplicate equivalent observations, not nearby geometry or conflicting
        # action/provenance evidence. IDs remain scoped to their observation.
        identity = json.dumps(
            [
                role,
                label,
                [value or 0.0 for value in (box.x1, box.y1, box.x2, box.y2)],
                sorted(actions),
                confidence,
                source,
            ]
        )
        object_id = "obj_" + hashlib.sha256(identity.encode()).hexdigest()[:12]
        if object_id in seen:
            continue
        seen.add(object_id)
        objects.append(
            UIObject(
                id=object_id,
                bbox=box,
                label=label,
                role=role,
                confidence=confidence,
                actions=frozenset(actions),
                source=(source,),
                sensitive=sensitive,
            )
        )
    return tuple(objects)

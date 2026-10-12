"""Provenance-preserving compilation of observations into guarded runtime facts.

Only trusted local observation providers may supply evidence. Tool requests are
never evidence; visible labels alone do not establish application state.
"""

from __future__ import annotations

import time
from enum import StrEnum
from threading import Lock
from typing import Literal

from pydantic import Field, JsonValue

from .schema import Observation, StrictModel


class StateSource(StrEnum):
    UNAVAILABLE = "UNAVAILABLE"
    PIXELS = "PIXELS"
    NATIVE = "NATIVE"
    ACCESSIBILITY = "ACCESSIBILITY"
    APP_TELEMETRY = "APP_TELEMETRY"
    API = "API"


class FactValidity(StrEnum):
    UNKNOWN = "UNKNOWN"
    VALID = "VALID"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class StateFact(StrictModel):
    value: JsonValue = None
    source: StateSource = StateSource.UNAVAILABLE
    observed_at: float = Field(ge=0)
    state_version: int = Field(ge=1)
    validity: FactValidity = FactValidity.UNKNOWN
    uncertainty: float = Field(default=1, ge=0, le=1)


FACT_NAMES = (
    "application_snapshot",
    "editor_layout",
    "keymap_inventory",
    "application",
    "window",
    "foreground",
    "editor",
    "mode",
    "active_tool",
    "selection",
    "text_focus",
    "ime_composing",
    "keymap",
    "keymap_version",
    "modal",
    "popup",
    "loading",
    "target_geometry",
    "owned_inputs",
    "menus",
    "unit",
    "space",
    "transform_values",
    "transform_preview",
    "transform_context",
    "properties",
    "focused_property",
    "view_revision",
    "command_result",
)


class StateUnavailable(ValueError):
    pass


class CompiledState(StrictModel):
    observation_id: str
    version: int = Field(ge=1)
    compiled_at: float
    access_level: Literal[
        "PIXELS_ONLY", "ACCESSIBILITY_ASSISTED", "APP_TELEMETRY_ASSISTED", "API_ASSISTED"
    ]
    facts: dict[str, StateFact]

    def fact(self, name: str) -> StateFact:
        if name not in self.facts:
            raise StateUnavailable(f"unregistered state fact: {name}")
        return self.facts[name]

    def require(self, name: str, max_uncertainty: float = 0.1) -> JsonValue:
        fact = self.fact(name)
        if fact.validity != FactValidity.VALID or fact.uncertainty > max_uncertainty:
            raise StateUnavailable(f"{name}: {fact.validity}, uncertainty={fact.uncertainty}")
        return fact.value

    def invalidate_geometry(self) -> CompiledState:
        facts = dict(self.facts)
        facts["target_geometry"] = facts["target_geometry"].model_copy(
            update={"validity": FactValidity.INVALIDATED}
        )
        return self.model_copy(update={"facts": facts})

    def expire(self, max_age_seconds: float) -> CompiledState:
        now = time.time()
        return self.model_copy(
            update={
                "facts": {
                    name: fact.model_copy(update={"validity": FactValidity.STALE})
                    if fact.validity == FactValidity.VALID
                    and not 0 <= now - fact.observed_at <= max_age_seconds
                    else fact
                    for name, fact in self.facts.items()
                }
            }
        )


class StateCompiler:
    def __init__(self, max_age_seconds: float = 1.0):
        if not 0 < max_age_seconds <= 30:
            raise ValueError("fact lifetime must be in (0, 30] seconds")
        self.max_age_seconds = max_age_seconds
        self.version = 0
        self._lock = Lock()

    def compile(
        self, observation: Observation, evidence: dict[str, StateFact] | None = None
    ) -> CompiledState:
        now = time.time()
        with self._lock:
            self.version += 1
            version = self.version
        facts = {name: StateFact(observed_at=now, state_version=version) for name in FACT_NAMES}
        facts["target_geometry"] = StateFact(
            value={item.id: item.bbox.model_dump() for item in observation.objects},
            source=StateSource.PIXELS,
            observed_at=observation.frame.captured_at,
            state_version=version,
            validity=FactValidity.VALID,
            uncertainty=max(
                (
                    1 - item.confidence if item.confidence is not None else 1
                    for item in observation.objects
                ),
                default=0,
            ),
        )
        # A capture may know an actual foreground window handle. It does not
        # establish editor, application name, keymap, text focus, or a modal.
        if observation.frame.foreground_window is not None:
            for name, value in (
                ("window", str(observation.frame.foreground_window)),
                ("foreground", True),
            ):
                facts[name] = StateFact(
                    value=value,
                    source=StateSource.NATIVE,
                    observed_at=observation.frame.captured_at,
                    state_version=version,
                    validity=FactValidity.VALID,
                    uncertainty=0,
                )
        for name, fact in (evidence or {}).items():
            if name not in facts:
                raise ValueError(f"unregistered state fact: {name}")
            facts[name] = fact
        for name, fact in facts.items():
            if fact.validity == FactValidity.VALID and (
                fact.source == StateSource.UNAVAILABLE
                or fact.state_version != version
                or not 0 <= now - fact.observed_at <= self.max_age_seconds
            ):
                fact = fact.model_copy(update={"validity": FactValidity.STALE})
            facts[name] = fact
        sources = {fact.source for fact in facts.values() if fact.validity == FactValidity.VALID}
        level = "PIXELS_ONLY"
        for source, access in (
            (StateSource.ACCESSIBILITY, "ACCESSIBILITY_ASSISTED"),
            (StateSource.APP_TELEMETRY, "APP_TELEMETRY_ASSISTED"),
            (StateSource.API, "API_ASSISTED"),
        ):
            if source in sources:
                level = access
        return CompiledState(
            observation_id=observation.id,
            version=version,
            compiled_at=now,
            access_level=level,
            facts=facts,
        )

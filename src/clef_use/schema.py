from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class TextInput(StrictModel):
    value: str = Field(min_length=1, max_length=2048)
    target_label: str | None = Field(default=None, max_length=200)


class Contract(StrictModel):
    goal: str = Field(min_length=1, max_length=4000)
    success_conditions: list[str] = Field(default_factory=list, max_length=12)
    constraints: list[str] = Field(default_factory=list, max_length=12)
    max_steps: int = Field(default=30, ge=1, le=100)
    confidence_threshold: float = Field(default=0.55, ge=0.05, le=1)
    text_inputs: list[TextInput] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def bounded_strings(self):
        if not self.goal.strip() or any(
            not s.strip() or len(s) > 1000 for s in self.success_conditions + self.constraints
        ):
            raise ValueError("goal and conditions must contain bounded, nonempty text")
        return self


class BoundingBox(StrictModel):
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)
    x2: float = Field(ge=0, le=1)
    y2: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def positive_area(self):
        if self.x1 >= self.x2 or self.y1 >= self.y2:
            raise ValueError("bounding box must have positive area")
        return self

    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


Operation = Literal["click", "double_click", "focus", "type", "press", "hotkey", "scroll", "wait"]


class UIObject(StrictModel):
    id: str
    bbox: BoundingBox
    label: str = ""
    role: Literal["text", "icon", "input", "button", "unknown"] = "unknown"
    confidence: float | None = Field(default=None, ge=0, le=1)
    actions: frozenset[Operation] = frozenset()
    source: tuple[str, ...] = ("vision",)
    sensitive: bool = False


class ActionCandidate(StrictModel):
    id: str
    operation: Operation
    observation_id: str
    target: str | None = None
    description: str
    value: str | None = None

    def audit(self) -> dict:
        return {"id": self.id, "operation": self.operation, "target": self.target}


class Decision(StrictModel):
    action: str | None = None
    confidence: float = Field(ge=0, le=1)
    goal_probability: float = Field(default=0, ge=0, le=1)
    replan_probability: float = Field(default=0, ge=0, le=1)
    safety_probability: float = Field(default=0, ge=0, le=1)
    progress: float = Field(default=0, ge=0, le=1)
    condition_probabilities: tuple[float, ...] = ()

    @model_validator(mode="after")
    def valid_conditions(self):
        if any(not 0 <= p <= 1 for p in self.condition_probabilities):
            raise ValueError("condition probabilities must be finite probabilities")
        return self


class Status(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    NEEDS_REPLAN = "NEEDS_REPLAN"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    SAFETY_BLOCK = "SAFETY_BLOCK"
    NO_PROGRESS = "NO_PROGRESS"
    STEP_BUDGET_EXHAUSTED = "STEP_BUDGET_EXHAUSTED"
    ERROR = "ERROR"
    ABORTED = "ABORTED"


class SessionResult(StrictModel):
    session_id: str
    status: Status
    steps: int
    rounds: int
    last_action: dict | None
    confidence: float | None
    reason: str
    summary: str


@dataclass(frozen=True)
class Frame:
    image: Image.Image
    origin: tuple[int, int] = (0, 0)
    logical_size: tuple[int, int] | None = None
    foreground_window: int | None = None

    def point(self, bbox: BoundingBox) -> tuple[int, int]:
        width, height = self.logical_size or self.image.size
        x, y = bbox.center()
        return (
            self.origin[0] + min(width - 1, int(x * width)),
            self.origin[1] + min(height - 1, int(y * height)),
        )


@dataclass(frozen=True)
class Observation:
    id: str
    frame: Frame
    objects: tuple[UIObject, ...]


class ActionResult(StrictModel):
    ok: bool
    reason: str = "executed"

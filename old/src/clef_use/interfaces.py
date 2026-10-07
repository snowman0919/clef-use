from threading import Event
from typing import Protocol

from PIL import Image

from .schema import ActionCandidate, ActionResult, Contract, Decision, Frame, Observation, UIObject


class CaptureBackend(Protocol):
    def capture(self) -> Frame: ...


class PerceptionBackend(Protocol):
    def parse(self, image: Image.Image) -> tuple[UIObject, ...]: ...


class DecisionBackend(Protocol):
    def decide(
        self,
        observation: Observation,
        goal: Contract,
        candidates: tuple[ActionCandidate, ...],
        history: list[dict],
    ) -> Decision: ...


class ActionBackend(Protocol):
    def execute(
        self, action: ActionCandidate, observation: Observation, cancelled: Event
    ) -> ActionResult: ...
    def release(self) -> None: ...


class Verifier(Protocol):
    def change(self, before: Frame, after: Frame) -> float: ...
    def fingerprint(self, frame: Frame) -> bytes: ...

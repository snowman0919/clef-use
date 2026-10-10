"""Regression: a verified visual effect of the previous action must reach CLEF.

Reproduces the production dogfood failure (observations 1/2 in reici-production
clef_use_observations.md): a Blender viewport stroke genuinely changed geometry
(visible pixels inside the effect ROI), yet the next decision saw only the full
screen plus a stale object list, scored its own success conditions low, and the
runtime turned that into NEEDS_REPLAN "lacks required visible condition
evidence" (trials V27/V29/V39/V42/V43).
"""

from typing import NoReturn

import pytest
from PIL import Image, ImageDraw

from clef_use.benchmark import FixtureDesktop
from clef_use.config import Config
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import Contract, Decision, Frame


class StrokeChangesViewport(FixtureDesktop):
    """One action, then a localized viewport change inside the target region."""

    def __init__(self):
        super().__init__()
        self.action_count = 0

    def capture(self):
        image = Image.new("RGB", (400, 240), "white")
        draw = ImageDraw.Draw(image)
        draw.text((40, 60), "Open Settings", fill="black")
        if self.action_count:
            draw.rectangle((20, 20, 120, 110), fill="red")
        return Frame(image)

    def execute(self, action, observation, cancelled):
        self.action_count += 1
        return super().execute(action, observation, cancelled)


def test_verified_effect_is_delivered_as_evidence_to_next_decision():
    desktop = StrokeChangesViewport()
    seen = []

    class Recorder:
        def decide(self, observation, goal, candidates, history):
            seen.append(observation)
            if len(seen) == 1:
                chosen = next(a for a in candidates if a.operation == "click")
                return Decision(action=chosen.id, confidence=0.99)
            return Decision(
                mode="COMPLETED",
                confidence=0.99,
                goal_probability=0.99,
                condition_probabilities=(0.99,),
            )

    session = Session(
        Contract(goal="Move the chin band", success_conditions=["band moved"], max_steps=8)
    )
    executor = SessionRuntime(desktop, desktop, Recorder(), desktop, Config(settle_seconds=0))
    result = executor.execute(session)
    assert result["status"] == "COMPLETED", result
    assert len(seen) >= 2
    second = seen[1]
    assert second.evidence, "verified visible effect never reached the next observation"
    facts = [item for item in second.evidence if isinstance(item, dict)]
    assert any(fact.get("verification") == "VERIFIED" for fact in facts), facts
    vector = facts[0].get("roi_change_cells_8x8")
    assert vector and "1" in vector, "measured change vector missing from effect evidence"


def test_measured_pixel_change_does_not_relax_goal_completion():
    desktop = StrokeChangesViewport()
    seen = []

    class Recorder:
        def decide(self, observation, goal, candidates, history):
            seen.append(observation)
            if len(seen) == 1:
                chosen = next(a for a in candidates if a.operation == "click")
                return Decision(action=chosen.id, confidence=0.99)
            return Decision(
                mode="COMPLETED",
                confidence=0.99,
                goal_probability=0.84,
                condition_probabilities=(0.76,),
            )

    session = Session(
        Contract(goal="Move the chin band", success_conditions=["band moved"], max_steps=8)
    )
    result = SessionRuntime(
        desktop, desktop, Recorder(), desktop, Config(settle_seconds=0)
    ).execute(session)
    assert result["status"] == "NEEDS_REPLAN", result
    assert result["steps"] == desktop.action_count == 1
    assert len(seen) == 2
    facts = [item for item in seen[1].evidence if isinstance(item, dict)]
    assert any(
        fact.get("verification") == "VERIFIED" and fact.get("roi_visibly_changed") is True
        for fact in facts
    )
    assert result["blocker"]["kind"] == "COMPLETION_UNVERIFIED"
    observed = result["blocker"]["observed"]
    assert observed["required_probability"] == 0.9
    assert observed["goal"]["probability"] == 0.84
    assert observed["conditions"][0]["probability"] == 0.76


@pytest.mark.parametrize("execution_mode", ["AUTO", "ASSESS"])
@pytest.mark.parametrize(
    ("goal_probability", "condition_probability", "budget", "expected", "rounds"),
    [
        (0.84, 0.76, 3, "NEEDS_REPLAN", 1),
        (0.99, 0.8999, 3, "NEEDS_REPLAN", 1),
        (0.8999, 0.99, 3, "NEEDS_REPLAN", 1),
        (0.9, 0.9, 3, "COMPLETED", 2),
        (0.99, 0.99, 1, "STEP_BUDGET_EXHAUSTED", 1),
    ],
)
def test_prior_effect_does_not_replace_strong_fresh_completion(
    execution_mode, goal_probability, condition_probability, budget, expected, rounds
):
    seen = []

    class NoInputDesktop(StrokeChangesViewport):
        def decide(self, observation, goal, candidates, history):
            seen.append(observation)
            return Decision(
                mode="COMPLETED",
                confidence=0.99,
                goal_probability=goal_probability,
                condition_probabilities=(condition_probability,),
            )

        def execute(self, action, observation, cancelled) -> NoReturn:
            raise AssertionError("completion assessment must not repeat prior input")

    desktop = NoInputDesktop()
    desktop.action_count = 1
    session = Session(
        Contract(
            goal="Move the chin band",
            success_conditions=["band moved"],
            execution_mode=execution_mode,
            max_steps=budget,
        )
    )
    # An effect fixture carried from a prior turn is not a final-goal witness.
    session.last_effect = {
        "guidance_count": 0,
        "evidence": [{"verification": "VERIFIED", "roi_visibly_changed": True}],
    }
    result = SessionRuntime(desktop, desktop, desktop, desktop, Config(settle_seconds=0)).execute(
        session
    )
    assert result["status"] == expected, result
    assert result["steps"] == 0 and result["rounds"] == rounds
    assert desktop.action_count == 1
    assert seen[0].evidence == [{"verification": "VERIFIED", "roi_visibly_changed": True}]
    if expected == "COMPLETED":
        assert result["reason"] == "goal and conditions verified on two fresh observations"


def test_weak_completion_without_a_delivered_effect_requests_replan():
    # Same sub-0.9 probabilities WITHOUT any executed-and-measured effect in the
    # session must still escalate to NEEDS_REPLAN, never COMPLETED.
    desktop = StrokeChangesViewport()

    class ClaimOnly:
        def decide(self, observation, goal, candidates, history):
            return Decision(
                mode="COMPLETED",
                confidence=0.99,
                goal_probability=0.84,
                condition_probabilities=(0.76,),
            )

    session = Session(
        Contract(goal="Move the chin band", success_conditions=["band moved"], max_steps=4)
    )
    result = SessionRuntime(
        desktop, desktop, ClaimOnly(), desktop, Config(settle_seconds=0)
    ).execute(session)
    assert result["status"] == "NEEDS_REPLAN", result
    assert "lacks required visible condition evidence" in result["reason"]

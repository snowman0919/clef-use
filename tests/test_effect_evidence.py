"""Regression: a verified visual effect of the previous action must reach CLEF.

Reproduces the production dogfood failure (observations 1/2 in reici-production
clef_use_observations.md): a Blender viewport stroke genuinely changed geometry
(visible pixels inside the effect ROI), yet the next decision saw only the full
screen plus a stale object list, scored its own success conditions low, and the
runtime turned that into NEEDS_REPLAN "lacks required visible condition
evidence" (trials V27/V29/V39/V42/V43).
"""

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


def test_calibrated_completion_accepts_model_plus_measured_effect():
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
    assert result["status"] == "COMPLETED", result
    assert any(
        row.get("completion_basis") == "effect_evidence_plus_model" for row in session.history
    )


def test_calibrated_completion_needs_a_witness_not_a_bare_claim():
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

from clef_use.benchmark import FixtureDesktop
from clef_use.config import Config
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import Contract


def test_decision_context_carries_actual_actions_without_past_model_predictions():
    desktop = FixtureDesktop()
    contexts = []

    class Decision:
        def decide(self, observation, contract, candidates, history):
            contexts.append(list(history))
            return desktop.decide(observation, contract, candidates, history)

    runtime = SessionRuntime(desktop, desktop, Decision(), desktop, Config(settle_seconds=0))
    session = Session(Contract(goal="Open Settings and apply font size 16", max_steps=8))
    result = runtime.execute(session)
    assert result["status"] == "COMPLETED"
    assert contexts[0] == []
    assert contexts[1][0]["description"] == "Click button: Settings"
    assert contexts[2][1]["description"] == "Click button: Apply"
    assert all(
        {
            "operation",
            "description",
            "target",
            "expected_effect",
            "verification",
            "failure_kind",
            "readiness",
        }
        == set(row)
        for row in contexts[2]
    )
    assert all(row["verification"] == "VISUAL_READINESS_ONLY" for row in contexts[2])
    assert all(row["readiness"] == "STABLE" for row in contexts[2])
    assert not any("confidence" in row or "goal_probability" in row for row in contexts[2])
    assert "decision_ms" in session.history[0]


def test_clef_modes_and_effect_use_one_joint_structured_worker_request():
    from types import SimpleNamespace

    from clef_use.backends import ClefBackend
    from clef_use.schema import Observation

    desktop = FixtureDesktop()
    observation = Observation("epoch", desktop.capture(), desktop.parse(None))
    backend = ClefBackend(Config())
    calls = []

    def request(payload):
        calls.append(payload)
        return {
            "answers": {
                "mode": {"choice": "WAIT", "confidence": 0.99},
                "effect": {"noul": 0.1},
                "action": {"choice": "none", "confidence": 1},
                "complete": {"noul": 0.01},
                "replan": {"noul": 0.01},
                "unsafe": {"noul": 0.01},
                "progress": {"score": 0},
                "condition_0": {"noul": 0.01},
            }
        }

    backend.worker = SimpleNamespace(request=request)
    decision = backend.decide(
        observation, Contract(goal="test", success_conditions=["done"]), (), []
    )
    assert len(calls) == 1 and decision.mode == "WAIT" and decision.action is None
    assert set(calls[0]["questions"]["mode"]["criteria"]) == {
        "ACT",
        "WAIT",
        "BLOCKED",
        "NEEDS_REPLAN",
        "COMPLETED",
    }
    assert calls[0]["questions"]["action"]["criteria"] == {"none": "No executable action available"}
    assert {q["type"] for q in calls[0]["questions"].values()} == {"choice", "noul", "score"}
    assert calls[0]["state"]["allowed_candidates"] == []


def test_unknown_actionability_is_omitted_from_model_state_without_claiming_true():
    from clef_use.backends import clef_request
    from clef_use.schema import Observation

    desktop = FixtureDesktop()
    observation = Observation("epoch", desktop.capture(), desktop.parse(None))
    payload = clef_request(observation, Contract(goal="test", success_conditions=["done"]), (), [])
    assert "enabled" not in payload["state"]["objects"][0]
    assert observation.objects[0].enabled is None
    assert list(payload["questions"])[-2:] == ["mode", "effect"]
    assert list(payload["questions"]).index("complete") < list(payload["questions"]).index(
        "condition_0"
    )


def test_dense_structured_session_still_receives_bounded_context():
    # Regression (dogfood F3): a 123-object Blender screen with 48 candidates
    # overflowed the real decision model's context via the legacy whole-roster
    # passthrough and crashed the CUDA worker with OUT_OF_MEMORY.
    from clef_use.backends import clef_request
    from clef_use.benchmark import FixtureDesktop
    from clef_use.config import Config
    from clef_use.runtime import Session, SessionRuntime
    from clef_use.schema import BoundingBox, Contract, Decision, UIObject

    class DenseBlender(FixtureDesktop):
        def parse(self, image):
            return tuple(
                UIObject(
                    id=str(i),
                    label=f"Scene Collection prop {i}",
                    actions=frozenset({"click"}),
                    bbox=BoundingBox(x1=0.1, y1=0.2, x2=0.6, y2=0.5),
                )
                for i in range(123)
            )

    sizes = []

    class SizeRecorder:
        def decide(self, observation, goal, candidates, history):
            payload = clef_request(observation, goal, candidates, history)
            sizes.append(len(payload["state"]["objects"]))
            return Decision(mode="WAIT", confidence=0.95)

    desktop = DenseBlender()
    session = Session(Contract(goal="Open the Object menu", max_steps=2))
    SessionRuntime(desktop, desktop, SizeRecorder(), desktop, Config(settle_seconds=0)).execute(
        session
    )
    assert sizes and max(sizes) <= 40  # 32 targets + 8 hints cap

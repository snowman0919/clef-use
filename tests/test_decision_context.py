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
    assert all(set(row) == {"operation", "description"} for row in contexts[2])
    assert "decision_ms" in session.history[0]

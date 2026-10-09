"""Real local ML on rendered pixels; intentionally performs no OS input."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from clef_use.backends import DecisionBackend, OmniParserBackend
from clef_use.config import load_config
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import ActionResult, Contract, Frame


class RenderedDesktop:
    def __init__(self):
        self.state = 0
        self.actions = []

    def capture(self):
        image = Image.new("RGB", (600, 400), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=28)
        draw.text((40, 40), "Local test workspace", font=font, fill="black")
        if self.state < 2:
            label = ("Continue", "Confirm")[self.state]
            draw.rectangle((50, 180, 260, 245), fill="#e5e7eb", outline="black", width=2)
            draw.text((70, 192), label, font=font, fill="black")
        else:
            draw.text((40, 180), "Task complete", font=font, fill="black")
        return Frame(image, (0, 0), image.size)

    def execute(self, action, observation, cancelled):
        target = next((o for o in observation.objects if o.id == action.target), None)
        self.actions.append(action.audit())
        expected = ("Continue", "Confirm")[self.state] if self.state < 2 else None
        if action.operation == "click" and target and expected.lower() in target.label.lower():
            self.state += 1
        return ActionResult(ok=not cancelled.is_set())

    def release(self):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("model-smoke.json"))
    args = parser.parse_args()
    config = load_config()
    desktop = RenderedDesktop()
    perception, decision = OmniParserBackend(config), DecisionBackend(config)
    session = Session(
        Contract(
            goal="Make Task complete visible using the available Continue and Confirm buttons.",
            success_conditions=["The text Task complete is visible"],
            max_steps=8,
        )
    )
    log = args.output.with_suffix(".steps.jsonl")
    runtime = SessionRuntime(desktop, perception, decision, desktop, config, log_path=log)
    start = time.perf_counter()
    try:
        result = runtime.execute(session)
    finally:
        perception.worker.close()
        decision.worker.close()
    result.update(
        mode="REAL_MODELS_SYNTHETIC_PIXELS",
        native_input=False,
        wall_seconds=time.perf_counter() - start,
        rendered_state=desktop.state,
        metrics=session.history,
        device=config.device,
        parser_device=config.parser_device,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "metrics"}, indent=2))
    return 0 if result["status"] == "COMPLETED" and desktop.state == 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())

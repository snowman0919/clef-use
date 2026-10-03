"""Real models on macOS controlling the disposable Windows GUI over private SSH."""

import argparse
import base64
import io
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

from clef_use.backends import ClefBackend, OmniParserBackend, encode_image
from clef_use.config import load_config
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import ActionResult, Contract, Frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=37944)
    args = parser.parse_args()
    token = args.token_file.read_text().strip()

    def request(operation, payload=None):
        req = urllib.request.Request(
            f"http://127.0.0.1:{args.port}/{operation}",
            data=json.dumps(payload or {}).encode(),
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(json.load(exc)) from None

    class Desktop:
        def capture(self):
            raw = request("capture")
            image = Image.open(io.BytesIO(base64.b64decode(raw["image"]))).convert("RGB")
            return Frame(image, tuple(raw["origin"]), tuple(raw["size"]), raw["foreground"])

        def execute(self, action, observation, cancelled):
            if cancelled.is_set():
                return ActionResult(ok=False, reason="aborted")
            result = request(
                "action",
                {
                    "action": action.model_dump(mode="json"),
                    "id": observation.id,
                    "objects": [o.model_dump(mode="json") for o in observation.objects],
                    "image": encode_image(observation.frame.image),
                    "origin": observation.frame.origin,
                    "size": observation.frame.image.size,
                    "foreground": observation.frame.foreground_window,
                },
            )
            return ActionResult.model_validate(result)

        def release(self):
            request("release")

    config = load_config()
    perception, decision, desktop = OmniParserBackend(config), ClefBackend(config), Desktop()
    session = Session(
        Contract(
            goal="Make Task complete visible using the available Continue and Confirm buttons.",
            success_conditions=["The text Task complete is visible"],
            max_steps=8,
        )
    )
    runtime = SessionRuntime(
        desktop,
        perception,
        decision,
        desktop,
        config,
        log_path=args.output.with_suffix(".steps.jsonl"),
    )
    started = time.perf_counter()
    result = {}
    try:
        result = runtime.execute(session)
        result["independent_gui_readback"] = request("result")
        result.update(
            mode="REAL_WINDOWS_GUI_MAC_MODELS_SSH_DIAGNOSTIC",
            native_input=True,
            inference_host="macOS",
            input_host="Windows 11",
            outer_interventions=0,
            wall_seconds=time.perf_counter() - started,
            metrics=session.history,
            device=config.device,
            parser_device=config.parser_device,
        )
    finally:
        perception.worker.close()
        decision.worker.close()
        request("finish")
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "metrics"}, indent=2))
    return (
        0
        if result.get("status") == "COMPLETED"
        and result.get("independent_gui_readback", {}).get("stage") == 2
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())

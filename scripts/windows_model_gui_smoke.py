"""Real models on macOS controlling the disposable Windows GUI over private SSH."""

import argparse
import base64
import io
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4

from PIL import Image

from clef_use.backends import ClefBackend, OmniParserBackend, encode_image
from clef_use.config import load_config, state_dir
from clef_use.runtime import Session, SessionRuntime
from clef_use.schema import ActionResult, Contract, Frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--port", type=int, default=37944)
    args = parser.parse_args()
    if args.output is None:
        args.output = state_dir() / "validation" / f"windows-model-{uuid4().hex}.json"
    args.output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Reserve before connecting or injecting input; never overwrite a prior experiment.
    with args.output.open("x", encoding="utf-8") as stream:
        os.chmod(args.output, 0o600)
        json.dump({"status": "STARTING", "benchmark": args.benchmark}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    print(f"Evidence: {args.output.resolve()}", flush=True)
    token = args.token_file.read_text().strip()

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_):
            raise RuntimeError("diagnostic bridge redirects refused")

    opener = urllib.request.build_opener(NoRedirect)

    def request(operation, payload=None):
        req = urllib.request.Request(
            f"http://127.0.0.1:{args.port}/{operation}",
            data=json.dumps(payload or {}).encode(),
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        )
        try:
            with opener.open(req, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(json.load(exc)) from None

    class Desktop:
        def capture(self):
            raw = request("capture")
            self.last_pending = raw.get("render_pending", False)
            image = Image.open(io.BytesIO(base64.b64decode(raw["image"]))).convert("RGB")
            return Frame(
                image,
                tuple(raw["origin"]),
                tuple(raw["size"]),
                raw["foreground"],
                tuple(raw["foreground_bounds"]),
            )

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
                    "foreground_bounds": observation.frame.foreground_bounds,
                },
            )
            return ActionResult.model_validate(result)

        def release(self):
            request("release")

    config = load_config()
    perception, decision, desktop = OmniParserBackend(config), ClefBackend(config), Desktop()
    if args.benchmark:
        from windows_visual_benchmark import run_benchmark

        try:
            accepted = run_benchmark(args, config, perception, decision, desktop, request)
        finally:
            perception.worker.close()
            decision.worker.close()
            request("finish")
        return 0 if accepted else 1
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
        from windows_visual_benchmark import save_report

        save_report(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k != "metrics"}, indent=2))
    return (
        0
        if result.get("status") == "COMPLETED"
        and result.get("independent_gui_readback", {}).get("stage") == 2
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())

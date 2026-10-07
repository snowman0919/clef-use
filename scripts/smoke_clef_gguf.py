"""Verify CLEF typed answers with a standalone, loopback-only llama.cpp server."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--server", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    base = f"http://127.0.0.1:{port}"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with args.output.with_suffix(".server.log").open("w") as log:
        process = subprocess.Popen(
            [
                str(args.server.resolve()),
                "-m",
                str(args.model.resolve()),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--threads",
                "4",
                "--parallel",
                "1",
                "--ctx-size",
                "1024",
                "--batch-size",
                "1024",
                "--ubatch-size",
                "1024",
                "--n-gpu-layers",
                "0",
            ],
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 180
            while True:
                if process.poll() is not None:
                    raise RuntimeError("server exited before readiness; inspect server log")
                try:
                    with urllib.request.urlopen(base + "/health", timeout=2) as response:
                        if response.status == 200:
                            break
                except (OSError, urllib.error.HTTPError):
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError("server readiness timeout")
                time.sleep(0.5)
            load_seconds = time.monotonic() - started
            records = []
            for displayed in (4, 5):
                body = {
                    "state": f"The displayed result is {displayed}.",
                    "questions": {
                        "number": {
                            "type": "choice",
                            "instructions": "Which number is displayed?",
                            "criteria": {"4": "Four", "5": "Five"},
                        },
                        "is_four": {
                            "type": "noul",
                            "instructions": "Is the displayed result four?",
                        },
                        "number_score": {
                            "type": "score",
                            "instructions": "What number is displayed?",
                            "criteria": ["Zero", "One", "Two", "Three", "Four", "Five"],
                        },
                    },
                }
                request = urllib.request.Request(
                    base + "/v1/systemone",
                    data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json"},
                )
                requested = time.monotonic()
                with urllib.request.urlopen(request, timeout=180) as response:
                    result = json.load(response)
                answers = result["answers"]
                assert answers["number"]["choice"] == str(displayed), result
                assert (answers["is_four"]["noul"] > 0.5) == (displayed == 4), result
                assert abs(answers["number_score"]["score"] - displayed) < 0.5, result
                assert abs(sum(answers["number"]["probabilities"].values()) - 1) < 0.001, result
                records.append(
                    {
                        "displayed": displayed,
                        "seconds": time.monotonic() - requested,
                        "response": result,
                    }
                )
            body["images"] = [
                "data:image/png;base64,"
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
            ]
            request = urllib.request.Request(
                base + "/v1/systemone",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
            )
            try:
                urllib.request.urlopen(request, timeout=30).close()
                raise RuntimeError("pinned text-only model unexpectedly accepted an image")
            except urllib.error.HTTPError as error:
                if error.code != 501:
                    raise
                image_error = json.loads(error.read())
            status = Path(f"/proc/{process.pid}/status").read_text()
            memory = [line for line in status.splitlines() if line.startswith(("VmHWM:", "VmRSS:"))]
            evidence = {
                "status": "PASSED",
                "mode": "CPU text-only",
                "load_seconds": load_seconds,
                "records": records,
                "image_input": {"http_status": 501, "response": image_error},
                "memory": memory,
                "limits": [
                    "No BF16 parity or broad accuracy benchmark",
                    "CLEF image input unsupported",
                    "No canonical runtime integration or GUI input",
                ],
            }
            args.output.write_text(json.dumps(evidence, indent=2) + "\n")
            print(json.dumps(evidence, indent=2))
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .client import RuntimeClient
from .config import load_config
from .deployment_profiles import PROFILES, profile_catalog
from .schema import Contract, TextInput


def parser():
    root = argparse.ArgumentParser(prog="clef-use")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="execute a high-level GUI goal")
    run.add_argument("goal")
    run.add_argument("--success", action="append", default=[])
    run.add_argument("--constraint", action="append", default=[])
    run.add_argument("--max-steps", type=int)
    run.add_argument("--confidence-threshold", type=float)
    run.add_argument("--text", action="append", default=[])
    for command in ("status", "abort", "observe"):
        sub = commands.add_parser(command)
        sub.add_argument("--session-id")
    resume = commands.add_parser("continue")
    resume.add_argument("session_id")
    resume.add_argument("instruction")
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--no-capture", action="store_true")
    models = commands.add_parser("models")
    models.add_argument(
        "action", choices=["list", "download", "prepare", "profiles"], nargs="?", default="list"
    )
    models.add_argument("--python")
    models.add_argument(
        "--rocm-arch", help="Windows ROCm ISA, e.g. gfx1150; autodetected when available"
    )
    models.add_argument("--profile", choices=["auto", "default", *PROFILES], default="auto")
    models.add_argument("--quantization", choices=["none", "4bit"])
    commands.add_parser("mcp")
    install = commands.add_parser("install-mcp")
    install.add_argument("harness", choices=["codex", "hermes", "omp"])
    install.add_argument("--path", type=Path)
    install.add_argument("--command-path")
    install.add_argument("--dry-run", action="store_true")
    update = commands.add_parser("update")
    update.add_argument("--base-url", default="https://ftp.kotori9.dev/clef-use")
    update.add_argument("--allow-insecure-localhost", action="store_true")
    commands.add_parser("version")
    commands.add_parser("self-test", help="offline deterministic runtime smoke check")
    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("--repetitions", type=int, default=5)
    benchmark.add_argument(
        "--tasks", type=Path, help="JSON contract list; executes real desktop input"
    )
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "mcp":
            from .mcp_server import main as serve

            serve()
            return 0
        if args.command == "version":
            print(__version__)
            return 0
        if args.command == "run":
            config = load_config()
            contract = Contract(
                goal=args.goal,
                success_conditions=args.success,
                constraints=args.constraint,
                max_steps=args.max_steps if args.max_steps is not None else config.max_steps,
                confidence_threshold=args.confidence_threshold
                if args.confidence_threshold is not None
                else config.confidence_threshold,
                text_inputs=[TextInput(value=v) for v in args.text],
            )
            result = RuntimeClient().run(contract)
        elif args.command in {"status", "abort", "observe"}:
            result = RuntimeClient(start=False).request(args.command, session_id=args.session_id)
        elif args.command == "continue":
            result = RuntimeClient(start=False).continue_session(args.session_id, args.instruction)
        elif args.command == "doctor":
            from .doctor import doctor

            result = doctor(not args.no_capture)
        elif args.command == "install-mcp":
            from .harness import install_mcp

            result = install_mcp(args.harness, args.path, args.command_path, args.dry_run)
        elif args.command == "models":
            from .models import MODEL_REVISIONS, download, inventory

            config = load_config()
            if args.action == "profiles":
                print(json.dumps(profile_catalog(), indent=2))
                return 0
            if args.action == "prepare":
                from .provision import prepare

                result = prepare(
                    config, args.python, args.profile, args.quantization, args.rocm_arch
                )
            else:
                if args.action == "download":
                    for model in [
                        config.decision_model,
                        "microsoft/OmniParser-v2.0",
                        "microsoft/Florence-2-base",
                        "microsoft/Florence-2-base-ft",
                    ]:
                        download(config.model_dir, model)
                result = {
                    "revisions": MODEL_REVISIONS,
                    "models": inventory(config.model_dir, config.decision_model),
                }
        elif args.command in {"benchmark", "self-test"}:
            from .benchmark import desktop_benchmark, fixture_benchmark

            repetitions = args.repetitions if args.command == "benchmark" else 1
            if not 1 <= repetitions <= 100:
                raise ValueError("repetitions must be 1 to 100")
            tasks = args.tasks if args.command == "benchmark" else None
            result = (
                desktop_benchmark(tasks, repetitions) if tasks else fixture_benchmark(repetitions)
            )
            if not all(s["task_success"] for s in result["samples"]):
                print(json.dumps(result))
                return 1
        elif args.command == "update":
            from .installer import install

            result = install(args.base_url, args.allow_insecure_localhost)
        print(json.dumps(result, indent=2))
        if args.command == "run" and result["status"] != "COMPLETED":
            return 2
        if args.command == "doctor" and not result["ready"]:
            return 2
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "type": type(exc).__name__,
                    "reason": str(exc)
                    if isinstance(exc, (ValueError, RuntimeError))
                    else "operation failed; run doctor",
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

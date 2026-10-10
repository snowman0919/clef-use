from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .client import RuntimeClient
from .config import load_config
from .deployment_profiles import PROFILES, profile_catalog
from .models import DECISION_MODELS
from .schema import Contract, TextInput, VisualIntent


def parser():
    root = argparse.ArgumentParser(
        prog="clef-use",
        description="Local GUI automation through a shared CLI/MCP runtime.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "First use (model preparation is required):\n"
            "  clef-use models prepare   # install inference dependencies and download models\n"
            "  clef-use doctor           # check models and desktop permissions\n"
            '  clef-use run "your GUI goal"\n\n'
            "Model preparation requires Python 3.11/3.12, Git and sufficient disk space.\n"
            "See: https://github.com/snowman0919/clef-use/blob/main/docs/INSTALL.md"
        ),
    )
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="execute a high-level GUI goal")
    run.add_argument("goal")
    run.add_argument("--success", action="append", default=[])
    run.add_argument("--constraint", action="append", default=[])
    run.add_argument(
        "--mode", choices=["AUTO", "STRUCTURED", "VISUAL", "CANVAS", "ASSESS"], default="AUTO"
    )
    run.add_argument("--visual-query")
    run.add_argument("--coarse-strategy", choices=("tiled", "overview"), default="tiled")
    run.add_argument("--max-steps", type=int)
    run.add_argument("--confidence-threshold", type=float)
    run.add_argument("--text", action="append", default=[])
    for command in ("status", "abort", "observe"):
        sub = commands.add_parser(
            command,
            help={
                "status": "show session progress and terminal result",
                "abort": "cancel the active GUI task",
                "observe": "inspect the session screen and controls",
            }[command],
        )
        sub.add_argument("--session-id")
        if command == "observe":
            sub.add_argument(
                "--cached",
                action="store_true",
                help="read recorded evidence without capture or service startup",
            )
    resume = commands.add_parser("continue", help="resume a session with new guidance")
    resume.add_argument("session_id")
    resume.add_argument("instruction")
    doctor = commands.add_parser(
        "doctor", aliases=["docker"], help="diagnose or repair model setup"
    )
    doctor.add_argument("--no-capture", action="store_true")
    doctor.add_argument(
        "--fix",
        action="store_true",
        help="repair missing model dependencies and weights",
    )
    commands.add_parser("uninstall", help="remove the managed runtime; retain models and settings")
    models = commands.add_parser(
        "models",
        help="prepare inference dependencies and download or inspect models",
        description=(
            "The installer can run model preparation after asking Y/n. "
            "Run 'clef-use models prepare' "
            "before your first GUI task; it installs inference dependencies, downloads "
            "missing models and saves configuration after initialization succeeds."
        ),
    )
    models.add_argument(
        "action",
        choices=["list", "download", "prepare", "profiles"],
        nargs="?",
        default="list",
        help=(
            "list: cached models; download: weights only; "
            "prepare: full setup; profiles: OS/backend choices"
        ),
    )
    models.add_argument(
        "--json", action="store_true", help="suppress setup progress; emit JSON result"
    )
    models.add_argument("--python")
    models.add_argument(
        "--decision-model",
        choices=list(DECISION_MODELS),
        help="prepare or inspect a pinned candidate without activating it",
    )
    models.add_argument(
        "--visual", action="store_true", help="download the configured visual backbone"
    )
    models.add_argument(
        "--rocm-arch", help="Windows ROCm ISA, e.g. gfx1150; autodetected when available"
    )
    models.add_argument("--profile", choices=["auto", "default", *PROFILES], default="auto")
    models.add_argument(
        "--quantization",
        choices=["none", "4bit"],
        help="none: original weights; 4bit: bitsandbytes NF4 during loading",
    )
    commands.add_parser("mcp", help="start the MCP server for an AI agent")
    install = commands.add_parser("install-mcp", help="register clef-use with Codex, Hermes or OMP")
    install.add_argument("harness", choices=["codex", "hermes", "omp"])
    install.add_argument("--path", type=Path)
    install.add_argument("--command-path")
    install.add_argument("--dry-run", action="store_true")
    update = commands.add_parser("update", help="update the runtime while retaining model cache")
    update.add_argument("--base-url", default="https://ftp.kotori9.dev/clef-use")
    update.add_argument("--allow-insecure-localhost", action="store_true")
    commands.add_parser("version", help="show the installed runtime version")
    commands.add_parser("self-test", help="offline deterministic runtime smoke check")
    benchmark = commands.add_parser(
        "benchmark", help="measure runtime behavior; --tasks performs real GUI input"
    )
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
                execution_mode=args.mode,
                visual_intent=(
                    VisualIntent(
                        query=args.visual_query or args.goal, coarse_strategy=args.coarse_strategy
                    )
                    if args.visual_query or args.coarse_strategy != "tiled"
                    else None
                ),
            )
            result = RuntimeClient().run(contract)
        elif args.command == "observe":
            result = RuntimeClient(start=False).request(
                "observe", session_id=args.session_id, refresh=not args.cached
            )
        elif args.command in {"status", "abort"}:
            result = RuntimeClient(start=False).request(args.command, session_id=args.session_id)
        elif args.command == "continue":
            result = RuntimeClient(start=False).continue_session(args.session_id, args.instruction)
        elif args.command in {"doctor", "docker"}:
            from .maintenance import diagnose

            result = diagnose(not args.no_capture, args.fix)
        elif args.command == "uninstall":
            from .maintenance import uninstall

            result = uninstall()
        elif args.command == "install-mcp":
            from .harness import install_mcp

            result = install_mcp(args.harness, args.path, args.command_path, args.dry_run)
        elif args.command == "models":
            from .models import MODEL_REVISIONS, download, inventory

            config = load_config()
            if args.visual and args.action not in {"download", "list"}:
                raise ValueError("--visual applies to models download or list")
            if args.action == "profiles":
                print(json.dumps(profile_catalog(), indent=2))
                return 0
            if args.action == "prepare":
                from .provision import prepare

                result = prepare(
                    config,
                    args.python,
                    args.profile,
                    args.quantization,
                    args.rocm_arch,
                    decision_model=args.decision_model,
                    progress=None
                    if args.json
                    else lambda message: print(message, file=sys.stderr, flush=True),
                )
            else:
                selected_model = args.decision_model or config.decision_model
                if args.action == "download":
                    models = [
                        selected_model,
                        "microsoft/OmniParser-v2.0",
                        "microsoft/Florence-2-base",
                        "microsoft/Florence-2-base-ft",
                    ]
                    if args.visual:
                        if config.visual_model not in MODEL_REVISIONS:
                            raise ValueError("visual download requires a supported pinned model")
                        models = [config.visual_model]
                    for model in models:
                        download(config.model_dir, model)
                result = {
                    "revisions": MODEL_REVISIONS,
                    "active_decision_model": config.decision_model,
                    "selected_decision_model": selected_model,
                    "models": inventory(
                        config.model_dir,
                        selected_model,
                        visual=args.visual or config.visual_grounding,
                    ),
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
        if args.command in {"doctor", "docker"} and not result["ready"]:
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

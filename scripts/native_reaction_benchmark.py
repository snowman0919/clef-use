"""Predeclared, isolated native Tk reaction benchmark; never a release gate.

The Tk event loop lives in a separate process. Its KeyPress timestamp is taken
before class bindings insert text, then verified after that insertion. Thus the
legacy injector's post-injection pause cannot postpone the receiver timestamp.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path


def percentile(values, probability):
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * probability) - 1] if ordered else None


def summarize(rows, elapsed_seconds, target_ms):
    correct = [row for row in rows if row["verified"] and not row["critical_errors"]]
    latencies = [row["event_latency_ms"] for row in correct if row["event_latency_ms"] is not None]
    fast = sum(value <= target_ms for value in latencies)
    eligibility_known = bool(rows) and all(type(row.get("fast_eligible")) is bool for row in rows)
    return {
        "opportunities": len(rows),
        "correct": len(correct),
        "accuracy": len(correct) / len(rows) if rows else None,
        "fast_correct": fast,
        "goodput_100": sum(value <= 100 for value in latencies) / len(rows) if rows else None,
        "fast_coverage": sum(row["fast_eligible"] for row in rows) / len(rows)
        if eligibility_known
        else None,
        "fast_coverage_status": "MEASURED" if eligibility_known else "NOT_MEASURED",
        "misses": len(rows) - fast,
        "critical_errors": sum(len(row["critical_errors"]) for row in rows),
        "failed_opportunities": len(rows) - len(correct),
        "goodput_per_second": len(correct) / elapsed_seconds if elapsed_seconds else None,
        "elapsed_seconds": elapsed_seconds,
        "correct_event_latency_ms": {
            name: percentile(latencies, probability)
            for name, probability in (("p50", 0.5), ("p95", 0.95), ("p99", 0.99))
        },
    }


TK_APP = r"""
import json,sys,time,tkinter as tk
root=tk.Tk()
root.geometry("620x440+30+40")
root.title("Owned clef-use benchmark fixture")
task=tk.Label(root,text="ready")
task.pack()
entry=tk.Entry(root)
entry.pack(fill="x")
editor=tk.Text(root,width=70,height=15)
editor.pack()
expected=None
current=None
started=None
active=entry
received=[]
observe_text=False
capture_keys=True
def emit(value):
    print(json.dumps(value,ensure_ascii=True),flush=True)
def content():
    return entry.get() if active is entry else editor.get("1.0","end-1c")
def key(event):
    if not event.char or not capture_keys: return
    event_ns=time.perf_counter_ns()
    identity=current
    received.append(dict(id=identity,keysym=event.keysym,char=event.char,received_ns=event_ns))
    def verify():
        emit(dict(kind="received",id=identity,event_ns=event_ns,
                  keysym=event.keysym,char=event.char,widget=content(),expected=expected,
                  verified_ns=time.perf_counter_ns()))
    root.after_idle(verify)
entry.bind("<KeyPress>",key)
editor.bind("<KeyPress>",key)
def modified(event):
    if not editor.edit_modified(): return
    editor.edit_modified(False)
    if observe_text and active is editor and content()==expected:
        emit(dict(kind="text_effect",id=current,widget=content(),
                  verified_ns=time.perf_counter_ns()))
editor.bind("<<Modified>>",modified)
def command(stream,mask):
    global expected,current,started,active,observe_text,capture_keys
    line=sys.stdin.readline()
    if not line:
        root.destroy();return
    request=json.loads(line)
    if request["op"]=="prepare":
        current=request["id"]
        expected=request["expected"]
        observe_text=request.get("observe_text",False)
        capture_keys=request.get("capture_keys",True)
        active=editor if request.get("editor") else entry
        if active is entry: entry.delete(0,"end")
        else: editor.delete("1.0","end")
        active.focus_force()
        started=time.perf_counter_ns()
        task.configure(text=expected)
        emit(dict(kind="prepared",id=current,started_ns=started,
                  task=task.cget("text"),widget=content()))
    elif request["op"]=="inspect":
        emit(dict(kind="inspected",id=request["id"],widget=content(),received=received))
    elif request["op"]=="quit":
        root.destroy()
root.createfilehandler(sys.stdin,tk.READABLE,command)
root.update()
entry.focus_force()
root.update()
emit(dict(kind="ready",pid=__import__("os").getpid()))
root.mainloop()
"""


def runtime_metadata(python, checkout):
    program = r"""
import hashlib,importlib.metadata,json,sys
from pathlib import Path
if sys.argv[1]:sys.path.insert(0,str(Path(sys.argv[1])/"src"))
import clef_use
root=Path(clef_use.__file__).parent
names=["backends.py","input_ir.py","x11_input_state.py","x11_clipboard.py","windows_input.py","schema.py"]
print(json.dumps(dict(python=sys.version,executable=sys.executable,
    package_version=importlib.metadata.version("clef-use"),module_origin=str(root),
    source_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest()
                   for name in names if (root/name).is_file()})))
"""
    result = subprocess.run(
        [python, "-c", program, str(checkout) if checkout else ""],
        capture_output=True,
        text=True,
        check=True,
        cwd=tempfile.gettempdir(),
    )
    return json.loads(result.stdout)


def _reader(process, replies):
    for line in process.stdout:
        try:
            replies.put(json.loads(line))
        except ValueError:
            pass  # Xlib may write an Xauthority diagnostic before protocol output.
    replies.put({"kind": "exit", "returncode": process.poll()})


def driver(config):
    if config["checkout"]:
        sys.path.insert(0, str(Path(config["checkout"]) / "src"))
    import pyautogui
    from PIL import Image
    from Xlib import display

    from clef_use.backends import DesktopAction, DesktopCapture
    from clef_use.input_ir import KeyInput
    from clef_use.schema import ActionCandidate, Frame, Observation

    replies = queue.Queue()
    app = subprocess.Popen(
        [sys.executable, "-c", TK_APP],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    threading.Thread(target=_reader, args=(app, replies), daemon=True).start()
    rows, editor_rows, preflight = [], [], {}
    baseline_spec = importlib.util.spec_from_file_location(
        "clef_use._baseline_backends", config["baseline_file"]
    )
    baseline = importlib.util.module_from_spec(baseline_spec)
    sys.modules[baseline_spec.name] = baseline
    baseline_spec.loader.exec_module(baseline)
    adapters = {
        "pinned_b3": baseline.DesktopAction(pyautogui),
        "current_legacy": DesktopAction(pyautogui),
        "typed": DesktopAction(pyautogui),
    }
    from threading import Event

    cancelled = {variant: Event() for variant in adapters}
    session_start = time.perf_counter_ns()
    try:
        assert replies.get(timeout=10)["kind"] == "ready"
        foreground, bounds = DesktopCapture._x11_context()
        frame = Frame(
            Image.new("RGB", (800, 600)), foreground_window=foreground, foreground_bounds=bounds
        )
        observation = Observation("owned-native-task", frame, ())

        def request(value, kind):
            app.stdin.write(json.dumps(value) + "\n")
            app.stdin.flush()
            reply = replies.get(timeout=3)
            if reply["kind"] != kind or reply.get("id") != value["id"]:
                raise RuntimeError(f"unexpected fixture event: {reply['kind']}")
            return reply

        def opportunity(variant, identity, cold, editor=False, task_index=None):
            row = {
                "variant": variant,
                "id": identity,
                "session": config["session"],
                "task_index": identity if task_index is None else task_index,
                "phase": "cold" if cold else "warm",
                "verified": False,
                "event_latency_ms": None,
                "critical_errors": [],
                "error": None,
                "source": "native Tk Text" if editor else "native Tk Entry",
            }
            opportunity_started = time.perf_counter_ns()
            try:
                prepared = request(
                    {
                        "op": "prepare",
                        "id": identity,
                        "expected": "a" if row["task_index"] % 2 == 0 else "b",
                        "editor": editor,
                    },
                    "prepared",
                )
                row["state_changed_ns"] = prepared["started_ns"]
                # Selection consumes the live task state returned by the widget,
                # rather than the independently known expected sequence.
                selected = prepared["task"]
                if variant == "typed":
                    result = adapters[variant].execute_input(
                        KeyInput(key=selected), frame, cancelled[variant]
                    )
                else:
                    result = adapters[variant].execute(
                        ActionCandidate(
                            id=str(identity),
                            operation="type",
                            target=None,
                            description="Insert the inspected task literal",
                            value=selected,
                            observation_id=observation.id,
                        ),
                        observation,
                        cancelled[variant],
                    )
                row["adapter_ok"] = result.ok
                received = replies.get(timeout=3)
                if received["kind"] != "received" or received.get("id") != identity:
                    row["critical_errors"].append("unexpected_native_event")
                    raise RuntimeError("native event did not belong to this opportunity")
                row.update(
                    received_ns=received["event_ns"],
                    verified_ns=received["verified_ns"],
                    expected=prepared["task"],
                    actual=received["widget"],
                    actual_key=received["char"],
                )
                row["event_latency_ms"] = (received["event_ns"] - prepared["started_ns"]) / 1e6
                row["verified"] = (
                    result.ok
                    and received["widget"] == prepared["task"]
                    and received["char"] == prepared["task"]
                )
                if received["widget"] != prepared["task"]:
                    row["critical_errors"].append("wrong_widget_state")
                if received["char"] != prepared["task"]:
                    row["critical_errors"].append("wrong_os_key")
                connection = display.Display()
                try:
                    if any(connection.query_keymap()):
                        row["critical_errors"].append("held_os_key_after_operation")
                finally:
                    connection.close()
                if adapters[variant].keys or adapters[variant].buttons:
                    row["critical_errors"].append("leaked_input_ownership")
            except Exception as exc:
                row["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                if app.poll() is not None:
                    row["critical_errors"].append("fixture_worker_exit")
                try:
                    adapters[variant].release()
                except Exception:
                    row["critical_errors"].append("cleanup_failure")
            row["attempt_started_ns"] = opportunity_started
            row["finished_ns"] = time.perf_counter_ns()
            row["attempt_seconds"] = (row["finished_ns"] - opportunity_started) / 1e9
            row["within_target"] = (
                row["verified"]
                and not row["critical_errors"]
                and row["event_latency_ms"] <= config["target_ms"]
            )
            return row

        # Exercise false guard against the independent real widget before samples.
        request({"op": "prepare", "id": -1, "expected": "a"}, "prepared")
        refused = False
        try:
            result = adapters["typed"].execute_input(
                KeyInput(key="a"), frame, cancelled["typed"], context_guard=lambda: False
            )
            refused = not result.ok
        except RuntimeError:
            refused = True
        observed = request({"op": "inspect", "id": -1}, "inspected")
        preflight["false_guard_blocks_native_event"] = (
            refused and observed["widget"] == "" and not observed["received"]
        )

        seen = {variant: 0 for variant in adapters}
        for batch in range(math.ceil(config["per_session"] / config["batch_size"])):
            variants = list(adapters)
            offset = (batch + config["session"]) % len(variants)
            order = variants[offset:] + variants[:offset]
            for variant in order:
                count = min(config["batch_size"], config["per_session"] - seen[variant])
                for _ in range(count):
                    identity = config["session"] * 1_000_000 + len(rows)
                    row = opportunity(
                        variant, identity, cold=seen[variant] == 0, task_index=seen[variant]
                    )
                    row["batch"] = batch
                    rows.append(row)
                    seen[variant] += 1
                print(
                    json.dumps(
                        {
                            "progress": True,
                            "session": config["session"],
                            "variant": variant,
                            "attempted": seen[variant],
                        }
                    ),
                    flush=True,
                )
        # Timed single-key Text widget profile; Unicode is a separate preflight.
        for index in range(10):
            editor_rows.append(
                opportunity(
                    "typed", 9_000_000 + config["session"] * 100 + index, cold=False, editor=True
                )
            )
        from clef_use.input_ir import TextInput

        unicode_text = "한😀 e\u0301"
        request(
            {
                "op": "prepare",
                "id": -2,
                "expected": unicode_text,
                "editor": True,
                "observe_text": True,
                "capture_keys": False,
            },
            "prepared",
        )
        result = adapters["typed"].execute_input(
            TextInput(text=unicode_text, method="clipboard"), frame, cancelled["typed"]
        )
        # Native clipboard transfer is not widget readback. Wait for the
        # independent app's actual edit event rather than an elapsed delay.
        effect = replies.get(timeout=3)
        if effect["kind"] != "text_effect" or effect.get("id") != -2:
            raise RuntimeError(f"unexpected Unicode effect event: {effect['kind']}")
        inspected = request({"op": "inspect", "id": -2}, "inspected")
        preflight["text_editor_exact_unicode"] = (
            result.ok and effect["widget"] == unicode_text and inspected["widget"] == unicode_text
        )
    except Exception as exc:
        preflight["driver_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
    finally:
        for adapter in adapters.values():
            try:
                adapter.release()
            except Exception:
                pass
        app.terminate()
        app.wait(timeout=5)
    # Account for every declared opportunity even if the fixture exits early.
    for variant in adapters:
        existing = sum(row["variant"] == variant for row in rows)
        for index in range(existing, config["per_session"]):
            rows.append(
                {
                    "variant": variant,
                    "id": f"unexecuted-{variant}-{index}",
                    "session": config["session"],
                    "phase": "cold" if index == 0 else "warm",
                    "verified": False,
                    "event_latency_ms": None,
                    "critical_errors": ["session_incomplete"],
                    "error": preflight.get("driver_error", "session did not finish"),
                    "attempt_seconds": 0,
                    "within_target": False,
                }
            )
    return {
        "rows": rows,
        "editor_rows": editor_rows,
        "preflight": preflight,
        "elapsed_seconds": (time.perf_counter_ns() - session_start) / 1e9,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runtime-python", default=sys.executable)
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--installed", action="store_true")
    parser.add_argument("--opportunities", type=int, default=1005)
    parser.add_argument("--sessions", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--diagnostic-smoke", action="store_true")
    parser.add_argument("--baseline-revision", default="b3f0b23309a7c7ea6a943e0c14e0ae51034552cd")
    parser.add_argument(
        "--baseline-repository", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--driver-config", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.driver_config:
        config = json.loads(args.driver_config.read_text())
        result = driver(config)
        Path(config["result_path"]).write_text(json.dumps(result, indent=2) + "\n")
        return
    if not args.output or args.installed and args.checkout:
        parser.error("--output and exactly one runtime selection are required")
    if not args.installed and not args.checkout:
        args.checkout = Path(__file__).resolve().parents[1]
    if (args.opportunities < 1000 or args.sessions < 5) and not args.diagnostic_smoke:
        parser.error("evidence requires >=1000 opportunities/variant and >=5 independent sessions")
    if args.opportunities <= 0 or args.sessions <= 0 or args.batch_size <= 0:
        parser.error("opportunities, sessions and batch-size must be positive")
    if args.opportunities % args.sessions:
        parser.error("opportunities must be divisible by sessions")
    if not shutil.which("Xvfb"):
        parser.error("Xvfb unavailable")
    args.output.mkdir(parents=True, exist_ok=True)
    scope_path = args.output / "BENCHMARK_SCOPE.json"
    if scope_path.exists():
        parser.error("scope already exists; choose a new output directory")
    metadata = runtime_metadata(args.runtime_python, args.checkout)
    baseline_source = subprocess.run(
        ["git", "show", f"{args.baseline_revision}:src/clef_use/backends.py"],
        cwd=args.baseline_repository,
        capture_output=True,
        check=True,
    ).stdout
    baseline_path = args.output / "pinned-baseline-backends.py"
    baseline_path.write_bytes(baseline_source)
    cpu = next(
        (
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        ),
        "unknown",
    )
    scope = {
        "schema_version": 1,
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "created_at": datetime.now(UTC).isoformat(),
        "scope": "Owned disposable Tk/Xvfb native task state -> selected OS key -> verified widget",
        "exclusions": [
            "Blender",
            "model inference",
            "screenshot state inference",
            "release gate",
            "full b3f0b23 runtime/model baseline",
            "real user desktop",
            "physical human input",
        ],
        "baseline_variant": {
            "revision": args.baseline_revision,
            "file": "src/clef_use/backends.py",
            "artifact": str(baseline_path.resolve()),
            "sha256": hashlib.sha256(baseline_source).hexdigest(),
            "supporting_libraries": (
                "current runtime schema/WindowsInput/candidates; plain ASCII Tk path only"
            ),
        },
        "variants": ["pinned_b3", "current_legacy", "typed"],
        "opportunities_per_variant": args.opportunities,
        "sessions": args.sessions,
        "batch_size": args.batch_size,
        "order": (
            "rotating variant order by session and batch; identical per-variant "
            "indexed alternating a/b task sequence"
        ),
        "cold": (
            "first opportunity of each variant per fresh driver/app session; "
            "interpreter/app startup excluded"
        ),
        "warm": "remaining opportunities; no dropped failures or deadline misses",
        "timing": (
            "monotonic perf_counter_ns; separate Tk process timestamps "
            "state change and OS KeyPress receipt"
        ),
        "verification": (
            "Tk after_idle readback after native class binding; "
            "expected key and literal must both match"
        ),
        "target_ms": 100,
        "accuracy_required": 1.0,
        "critical_errors_allowed": 0,
        "critical_errors": [
            "wrong_widget_state",
            "wrong_os_key",
            "unexpected_native_event",
            "held_os_key_after_operation",
            "leaked_input_ownership",
            "fixture_worker_exit",
            "cleanup_failure",
            "session_incomplete",
        ],
        "reporting": (
            "all failures count in accuracy/goodput denominators; "
            "eligibility coverage stays unmeasured; "
            "correct-only latency explicitly labelled"
        ),
        "generality": (
            "Timed native Tk Text single-key profile; separate Unicode clipboard correctness "
            "preflight has no latency percentile. Browser not covered."
        ),
        "diagnostic_only": args.diagnostic_smoke,
        "runtime": metadata,
        "environment": {
            "platform": platform.platform(),
            "cpu": cpu,
            "logical_cpus": os.cpu_count(),
            "loadavg_at_declaration": os.getloadavg(),
            "power_thermal": "NOT_CONTROLLED",
            "competing_load": "other workspace agents may be active",
        },
    }
    scope_path.write_text(json.dumps(scope, indent=2) + "\n")
    print(f"Predeclared scope: {scope_path}", flush=True)
    session_results = []
    with tempfile.TemporaryDirectory(prefix="clef-native-reaction-") as temporary:
        read_fd, write_fd = os.pipe()
        xvfb = subprocess.Popen(
            [
                "Xvfb",
                "-displayfd",
                str(write_fd),
                "-screen",
                "0",
                "800x600x24",
                "-nolisten",
                "tcp",
                "-ac",
            ],
            pass_fds=(write_fd,),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.close(write_fd)
        try:
            with os.fdopen(read_fd) as stream:
                display_number = stream.readline().strip()
            if not display_number.isdigit():
                raise RuntimeError("disposable Xvfb failed to allocate a display")
            authority = Path(temporary) / "Xauthority"
            authority.touch()
            environment = dict(os.environ, DISPLAY=f":{display_number}", XAUTHORITY=str(authority))
            for session in range(args.sessions):
                result_path = args.output / f"session-{session}.json"
                config = {
                    "checkout": str(args.checkout.resolve()) if args.checkout else None,
                    "session": session,
                    "per_session": args.opportunities // args.sessions,
                    "batch_size": args.batch_size,
                    "target_ms": 100,
                    "result_path": str(result_path.resolve()),
                    "baseline_file": str(baseline_path.resolve()),
                }
                config_path = Path(temporary) / "driver.json"
                config_path.write_text(json.dumps(config))
                log_path = args.output / f"session-{session}.log"
                try:
                    with log_path.open("w") as log:
                        subprocess.run(
                            [
                                args.runtime_python,
                                str(Path(__file__).resolve()),
                                "--driver-config",
                                str(config_path),
                            ],
                            env=environment,
                            cwd=temporary,
                            stdout=log,
                            stderr=subprocess.STDOUT,
                            timeout=max(90, config["per_session"] * 10),
                            check=True,
                        )
                except (subprocess.SubprocessError, OSError) as exc:
                    if not result_path.exists():
                        failed = {
                            "rows": [],
                            "editor_rows": [],
                            "preflight": {"driver_process_error": type(exc).__name__},
                            "elapsed_seconds": None,
                        }
                        for variant in scope["variants"]:
                            for index in range(config["per_session"]):
                                failed["rows"].append(
                                    {
                                        "variant": variant,
                                        "phase": "cold" if index == 0 else "warm",
                                        "verified": False,
                                        "event_latency_ms": None,
                                        "critical_errors": ["session_incomplete"],
                                        "error": type(exc).__name__,
                                        "attempt_seconds": 0,
                                        "executed": False,
                                        "session": session,
                                        "id": index,
                                    }
                                )
                        result_path.write_text(json.dumps(failed, indent=2) + "\n")
                session_results.append(json.loads(result_path.read_text()))
                print(f"Finished session {session + 1}/{args.sessions}: {result_path}", flush=True)
        finally:
            xvfb.terminate()
            xvfb.wait(timeout=5)
    rows = [row for session in session_results for row in session["rows"]]
    report = {
        "scope_sha256": hashlib.sha256(scope_path.read_bytes()).hexdigest(),
        "release_gate": "NOT_RUN",
        "scope": scope["scope"],
        "variants": {},
        "runtime_after": runtime_metadata(args.runtime_python, args.checkout),
        "preflight": [session["preflight"] for session in session_results],
    }
    for variant in scope["variants"]:
        selected = [row for row in rows if row["variant"] == variant]
        report["variants"][variant] = {
            phase: summarize(
                [row for row in selected if phase == "all" or row["phase"] == phase],
                sum(
                    row["attempt_seconds"]
                    for row in selected
                    if phase == "all" or row["phase"] == phase
                ),
                100,
            )
            for phase in ("all", "cold", "warm")
        }
        report["variants"][variant]["sessions"] = [
            summarize(
                [row for row in session["rows"] if row["variant"] == variant],
                sum(row["attempt_seconds"] for row in session["rows"] if row["variant"] == variant),
                100,
            )
            for session in session_results
        ]
    report["source_unchanged_during_run"] = report["runtime_after"] == metadata
    editor = [row for session in session_results for row in session["editor_rows"]]
    report["native_text_editor"] = summarize(
        editor, sum(row["attempt_seconds"] for row in editor), 100
    )
    report_path = args.output / "REPORT.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()

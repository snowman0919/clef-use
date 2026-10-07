"""Native Windows installer lifecycle evidence; deletes only its reserved installation."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--base-url", default="https://ftp.kotori9.dev/clef-use")
    parser.add_argument("--bootstrap-url", default="https://ftp.kotori9.dev/clef-use/install.ps1")
    parser.add_argument("--allow-insecure-localhost", action="store_true")
    parser.add_argument("--agent-script", type=Path)
    parser.add_argument("--gui-script", type=Path)
    parser.add_argument("--gui-config", type=Path)
    parser.add_argument("--rocm-worker", type=Path)
    args = parser.parse_args()
    if sys.platform != "win32":
        raise RuntimeError("native Windows is required")
    args.evidence.mkdir(parents=True, exist_ok=False)
    install_root = args.evidence / "managed-install"
    marker = uuid4().hex
    ownership = args.evidence / "ownership.txt"
    ownership.write_text(marker)
    report = {"mode": "NATIVE_WINDOWS_INSTALL_COMMAND_TO_REMOVAL", "steps": [], "errors": []}
    child_env = dict(os.environ)
    child_env.update(
        CLEF_USE_INSTALL_ROOT=str(install_root),
        CLEF_USE_BIN_DIR=str(install_root / "bin"),
        CLEF_USE_NO_PATH_UPDATE="1",
        CLEF_USE_PYTHON=sys.executable,
        CLEF_USE_RELEASE_BASE_URL=args.base_url,
        CLEF_USE_STATE_DIR=str(args.evidence / "state"),
        CLEF_USE_CONFIG=str(args.evidence / "config.toml"),
    )
    if args.gui_config:
        child_env["CLEF_USE_CONFIG"] = str(args.gui_config)
        report["configuration_mode"] = (
            "Existing task-owned models/environments, no global configuration edits"
        )
    else:
        Path(child_env["CLEF_USE_CONFIG"]).write_text("max_steps = 1\nbackend_timeout = 5\n")
        report["configuration_mode"] = (
            "Fresh defaults; model preparation not performed by the installer"
        )
    launcher = install_root / "bin/clef-use.cmd"
    installed_python = None
    gui_task = None

    def command(name, argv, timeout=120, env=None):
        started = time.perf_counter()
        completed = subprocess.run(
            argv,
            env=env or child_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        (args.evidence / (name + ".stdout.txt")).write_text(completed.stdout, encoding="utf-8")
        (args.evidence / (name + ".stderr.txt")).write_text(completed.stderr, encoding="utf-8")
        step = {
            "name": name,
            "exit_code": completed.returncode,
            "wall_seconds": time.perf_counter() - started,
        }
        report["steps"].append(step)
        print(json.dumps(step), flush=True)
        return completed

    def ps(name, code, timeout=120):
        import base64

        code = "$ProgressPreference = 'SilentlyContinue'; " + code
        encoded = base64.b64encode(code.encode("utf-16-le")).decode()
        return command(name, ["powershell.exe", "-NoProfile", "-EncodedCommand", encoded], timeout)

    def registry_path():
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "[Console]::Write([Environment]::GetEnvironmentVariable('Path','User'))",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout

    path_before = registry_path()
    global_root = Path(os.environ["LOCALAPPDATA"]) / "clef-use"
    global_launcher = global_root / "bin/clef-use.cmd"
    global_bytes = global_launcher.read_bytes() if global_launcher.is_file() else None
    report["global_install_existed"] = global_root.exists()
    report["installation_root"] = str(install_root)
    bootstrap = args.bootstrap_url.replace("'", "''")
    bootstrap_command = "irm '" + bootstrap + "' | iex"
    if args.allow_insecure_localhost:
        bootstrap_command = (
            "& ([ScriptBlock]::Create((irm '" + bootstrap + "'))) --allow-insecure-localhost"
        )
    report["installation_command"] = bootstrap_command
    try:
        result = ps("install-command", bootstrap_command, 600)
        if result.returncode or not launcher.is_file():
            raise RuntimeError("installation command did not activate its managed launcher")
        text = launcher.read_text()
        if "clef-use managed launcher" not in text:
            raise RuntimeError("installation launcher ownership marker missing")
        match = re.search(r'^@"([^"\r\n]+)" %\*$', text, re.MULTILINE)
        if not match:
            raise RuntimeError("managed launcher target malformed")
        target = match[1]
        executable = (
            (launcher.parent / target[5:]).resolve() if target.startswith("%~dp0") else Path(target)
        )
        if not executable.is_relative_to(install_root.resolve()):
            raise RuntimeError("managed executable escaped reserved installation")
        installed_python = executable.with_name("python.exe")
        report["installed_metadata"] = json.loads(
            (executable.parent.parent / "installed.json").read_text()
        )
        result = command(
            "installed-provenance",
            [
                str(installed_python),
                "-c",
                "import json,hashlib,clef_use; from pathlib import Path; "
                "p=Path(clef_use.__file__).parent; print(json.dumps({"
                "'version':clef_use.__version__,'package':str(p),"
                "'source_sha256':{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in "
                "['backends.py','model_worker.py','runtime.py','service.py']}}))",
            ],
        )
        report["installed_provenance"] = json.loads(result.stdout)
        ps(
            "installed-acl",
            "Get-Item ($env:CLEF_USE_INSTALL_ROOT), "
            "($env:CLEF_USE_INSTALL_ROOT + '/versions') | ForEach-Object { "
            "$acl = Get-Acl $_.FullName; "
            "[pscustomobject]@{Path=$_.FullName;Owner=$acl.Owner;"
            "Access=[string]$acl.AccessToString} "
            "} | ConvertTo-Json -Compress",
        )
        for name, options in (
            ("version", ["version"]),
            ("self-test", ["self-test"]),
            ("update", ["update", "--base-url", args.base_url]),
        ):
            if name == "update" and args.allow_insecure_localhost:
                options.append("--allow-insecure-localhost")
            result = command(name, [str(executable), *options], 180)
            if result.returncode:
                raise RuntimeError(name + " failed")
            if name == "self-test":
                report["self_test"] = json.loads(result.stdout)
        result = ps("reinstall-command", bootstrap_command, 600)
        if result.returncode:
            raise RuntimeError("idempotent installation command failed")
        result = command(
            "service-start",
            [
                str(installed_python),
                "-c",
                "import json; from clef_use.client import RuntimeClient; "
                "c=RuntimeClient(); c._ensure(); print(json.dumps(c._send('health', {})))",
            ],
        )
        if result.returncode:
            raise RuntimeError("installed runtime service failed to start")
        report["service_health"] = json.loads(result.stdout)
        mcp_code = """import asyncio, json, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def check():
    async with stdio_client(StdioServerParameters(command=sys.argv[1], args=["mcp"])) as (r, w):
        async with ClientSession(r, w) as client:
            await client.initialize()
            tools = await client.list_tools()
            print(json.dumps([tool.name for tool in tools.tools]))
asyncio.run(check())
"""
        result = command("mcp-handshake", [str(installed_python), "-c", mcp_code, str(executable)])
        if result.returncode:
            raise RuntimeError("installed MCP handshake failed")
        report["mcp_tools"] = json.loads(result.stdout)
        result = command(
            "run",
            [
                str(executable),
                "run",
                "Observe whether Task complete is visible without sending any input",
                "--success",
                "Task complete is visible",
                "--constraint",
                "Do not send keyboard or pointer input",
            ],
            60,
        )
        report["cli_run"] = (
            json.loads(result.stdout) if result.stdout.strip() else {"exit_code": result.returncode}
        )
        report["run_context"] = (
            "SSH Session 0; negative execution boundary, not a GUI success assertion"
        )
        for name in ("status", "observe", "abort"):
            command(name, [str(executable), name], 60)
        if args.gui_script:
            if not all((args.gui_config, args.agent_script, args.rocm_worker)):
                raise RuntimeError("GUI diagnostic requires config, private token file and worker")
            import secrets

            args.token_file = args.evidence / "gui-token"
            args.token_file.write_text(secrets.token_urlsafe(32))
            gui_task = "clef-use-lifecycle-" + marker[:12]

            def quote(value):
                return "'" + str(value).replace("'", "''") + "'"

            bootstrap = args.evidence / "gui-bootstrap.py"
            bootstrap.write_text(
                "import runpy,sys,traceback\nfrom pathlib import Path\n"
                "sys.argv="
                + repr([str(args.agent_script), "--root", str(args.evidence), "--port", "37945"])
                + "\n"
                "try: runpy.run_path(sys.argv[0],run_name='__main__')\n"
                "except BaseException:\n "
                "Path(__file__).with_suffix('.error.txt').write_text(traceback.format_exc()); "
                "raise\n"
            )
            action_args = '"' + str(bootstrap) + '"'
            result = ps(
                "gui-task-start",
                "$privateFile = " + quote(args.token_file) + "; "
                "$ownerSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
                "& icacls $privateFile /inheritance:r "
                "/grant:r ('*' + $ownerSid + ':(F)') | Out-Null; "
                "if ($LASTEXITCODE -ne 0) { throw 'Private token ACL failed' }; "
                "$action = New-ScheduledTaskAction -Execute "
                + quote(installed_python)
                + " -Argument "
                + quote(action_args)
                + " -WorkingDirectory "
                + quote(args.evidence)
                + "; "
                "$principal = New-ScheduledTaskPrincipal -UserId "
                "([Security.Principal.WindowsIdentity]::GetCurrent().Name) "
                "-LogonType Interactive -RunLevel Limited; "
                "$settings = New-ScheduledTaskSettingsSet "
                "-ExecutionTimeLimit (New-TimeSpan -Minutes 15) "
                "-AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; "
                "Register-ScheduledTask -TaskName "
                + quote(gui_task)
                + " -Action $action -Principal $principal -Settings $settings "
                "-ErrorAction Stop | Out-Null; "
                "Start-ScheduledTask -TaskName " + quote(gui_task) + " -ErrorAction Stop",
            )
            if result.returncode:
                raise RuntimeError("owned interactive GUI task failed to start")
            deadline = time.monotonic() + 30
            while (
                not (args.evidence / "windows-model-agent-ready.json").exists()
                and time.monotonic() < deadline
            ):
                time.sleep(0.1)
            result = ps(
                "gui-task-state",
                "$task = Get-ScheduledTask -TaskName " + quote(gui_task) + "; "
                "$info = Get-ScheduledTaskInfo -TaskName " + quote(gui_task) + "; "
                "[pscustomobject]@{State=[string]$task.State;LastTaskResult=$info.LastTaskResult} "
                "| ConvertTo-Json -Compress",
            )
            report["gui_task_state"] = json.loads(result.stdout)
            if not (args.evidence / "windows-model-agent-ready.json").exists():
                raise RuntimeError("owned interactive GUI endpoint did not become ready")
            gui_env = dict(child_env, CLEF_USE_CONFIG=str(args.gui_config), OMP_NUM_THREADS="12")
            output = args.evidence / "installed-model-gui.json"
            result = command(
                "installed-model-gui",
                [
                    str(installed_python),
                    str(args.gui_script),
                    "--token-file",
                    str(args.token_file),
                    "--port",
                    "37945",
                    "--rocm-worker",
                    str(args.rocm_worker),
                    "--output",
                    str(output),
                ],
                600,
                gui_env,
            )
            report["gui"] = (
                json.loads(output.read_text()) if output.exists() else {"status": "NOT_RECORDED"}
            )
            report["gui_scope"] = (
                "Installed package runtime with experimental NF4 loader and owned GUI bridge; "
                "not canonical CLI service GUI"
            )
            if result.returncode:
                raise RuntimeError("installed-package GUI diagnostic failed")
    except Exception as exc:
        report["errors"].append({"type": type(exc).__name__, "reason": str(exc)})
    finally:
        cleanup = {}
        if gui_task:
            result = ps(
                "gui-task-remove",
                "$ownedTask = Get-ScheduledTask -TaskName '"
                + gui_task
                + "' -ErrorAction SilentlyContinue; "
                "if ($ownedTask) { Stop-ScheduledTask -TaskName '"
                + gui_task
                + "' -ErrorAction Stop; "
                "Unregister-ScheduledTask -TaskName '"
                + gui_task
                + "' -Confirm:$false -ErrorAction Stop }; "
                "if (Get-ScheduledTask -TaskName '"
                + gui_task
                + "' -ErrorAction SilentlyContinue) { exit 4 }",
            )
            cleanup["gui_task_absent"] = result.returncode == 0
            args.token_file.unlink(missing_ok=True)
            cleanup["gui_token_absent"] = not args.token_file.exists()
            cleanup["gui_listener_absent"] = (
                ps(
                    "gui-listener-check",
                    "if (Get-NetTCPConnection -LocalPort 37945 -State Listen "
                    "-ErrorAction SilentlyContinue) { exit 5 }",
                ).returncode
                == 0
            )

        endpoint = Path(child_env["CLEF_USE_STATE_DIR"]) / "endpoint.json"
        if installed_python and endpoint.exists():
            result = command(
                "service-stop",
                [
                    str(installed_python),
                    "-c",
                    "import json; from clef_use.client import RuntimeClient; "
                    "c=RuntimeClient(start=False); print(json.dumps(c._send('shutdown_idle', {})))",
                ],
            )
            cleanup["shutdown_exit_code"] = result.returncode
            deadline = time.monotonic() + 15
            while endpoint.exists() and time.monotonic() < deadline:
                time.sleep(0.1)
        cleanup["endpoint_absent"] = not endpoint.exists()
        if ownership.read_text() != marker or install_root.parent != args.evidence:
            raise RuntimeError("reserved installation ownership changed; removal refused")
        if endpoint.exists():
            report["errors"].append(
                {"type": "CleanupRefused", "reason": "owned runtime did not stop"}
            )
        elif install_root.exists():
            shutil.rmtree(install_root)
        cleanup["install_root_absent"] = not install_root.exists()
        cleanup["launcher_absent"] = not launcher.exists()
        cleanup["user_path_unchanged"] = registry_path() == path_before
        cleanup["existing_launcher_unchanged"] = (
            global_launcher.read_bytes() if global_launcher.is_file() else None
        ) == global_bytes
        cleanup["owned_processes_absent"] = (
            ps(
                "process-check",
                "$rows = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and "
                "$_.ExecutablePath.StartsWith($env:CLEF_USE_INSTALL_ROOT + '\\', "
                "[StringComparison]::OrdinalIgnoreCase) }); "
                "if ($rows.Count) { exit 3 }; Write-Output 'No owned installed processes'",
            ).returncode
            == 0
        )
        report["cleanup"] = cleanup
        report["lifecycle_executed"] = not report["errors"] and all(
            value is True for key, value in cleanup.items() if key != "shutdown_exit_code"
        )
        report["canonical_cli_gui_success"] = False
        report["interactive_launch"] = (
            "Least-privilege interactive task directly runs unchanged installed Python. "
            "Installer grants only its same user directory access; "
            "no global security policy changes."
        )
        report["diagnostic_model_gui_success"] = report.get("gui", {}).get("status") == "COMPLETED"
        (args.evidence / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "lifecycle_executed": report["lifecycle_executed"],
                    "cleanup": cleanup,
                    "errors": report["errors"],
                }
            ),
            flush=True,
        )
    return 0 if report["lifecycle_executed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Canonical installer implementation; rendered into install.sh without package dependencies."""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import venv
import zipfile
from pathlib import Path

DEFAULT_BASE = "https://ftp.kotori9.dev/clef-use"


def validate_url(url, allow_local=False):
    parsed = urllib.parse.urlsplit(url)
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("URL credentials and fragments are refused")
    if parsed.scheme != "https":
        if not (
            allow_local
            and parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        ):
            raise ValueError("downloads require HTTPS; HTTP is limited to explicit loopback tests")
    if not parsed.hostname:
        raise ValueError("download URL needs a host")
    return parsed


def fetch(url, allow_local=False, limit=512 * 1024 * 1024, timeout=45):
    expected = validate_url(url, allow_local)

    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            target = validate_url(newurl, allow_local)
            if (target.scheme, target.netloc) != (expected.scheme, expected.netloc):
                raise ValueError("cross-origin download redirect refused")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(Redirect())
    request = urllib.request.Request(
        url, headers={"User-Agent": "clef-use/0.1 (+https://github.com/snowman0919/clef-use)"}
    )
    with opener.open(request, timeout=timeout) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("download exceeds size limit")
    return data


def release_version(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value
    ):
        raise ValueError("release version must be stable major.minor.patch")
    return tuple(map(int, value.split(".")))


def parse_manifest(raw, base_url, allow_local=False):
    data = json.loads(raw)
    if data.get("schema_version") != 1:
        raise ValueError("unsupported manifest schema")
    release_version(data["version"])
    if not isinstance(data.get("artifacts"), list) or not data["artifacts"]:
        raise ValueError("manifest has no artifacts")
    expected = validate_url(base_url, allow_local)
    for item in data["artifacts"]:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+\.zip", item["filename"]):
            raise ValueError("unsafe artifact filename")
        if not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError("invalid artifact checksum")
        url = validate_url(item["url"], allow_local)
        if (url.scheme, url.netloc) != (expected.scheme, expected.netloc):
            raise ValueError("artifact origin differs from configured release host")
        if item["platform"] not in {"darwin", "linux", "win32"} or item["architecture"] not in {
            "arm64",
            "x86_64",
        }:
            raise ValueError("unsupported platform in manifest")
        if item["python"] not in {"3.11", "3.12", "3.13"}:
            raise ValueError("unsupported Python requirement")
    return data


def select_artifact(manifest):
    machine = {"aarch64": "arm64", "amd64": "x86_64"}.get(
        platform.machine().lower(), platform.machine().lower()
    )
    python = f"{sys.version_info.major}.{sys.version_info.minor}"
    matches = [
        item
        for item in manifest["artifacts"]
        if (item["platform"], item["architecture"], item["python"])
        == (sys.platform, machine, python)
    ]
    if len(matches) != 1:
        available = ", ".join(
            f"{a['platform']}/{a['architecture']}/Python {a['python']}"
            for a in manifest["artifacts"]
        )
        raise ValueError(
            f"no unique compatible release for {sys.platform}/{machine}/Python {python}; "
            f"available: {available}"
        )
    return matches[0]


def verify_checksum(data, expected):
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("SHA-256 mismatch; previous installation preserved")


def safe_extract(archive: Path, destination: Path):
    with zipfile.ZipFile(archive) as payload:
        names = set()
        size = 0
        for member in payload.infolist():
            path = Path(member.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in member.filename
                or member.filename in names
                or (member.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("unsafe archive member")
            names.add(member.filename)
            size += member.file_size
        if size > 1024 * 1024 * 1024 or len(names) > 2000:
            raise ValueError("archive exceeds extraction limit")
        if "requirements.txt" not in names or not any(
            name.startswith("wheels/clef_use-") and name.endswith(".whl") for name in names
        ):
            raise ValueError("release missing runtime wheel or hashed requirements")
        payload.extractall(destination)


def atomic_text(path, text, mode=0o600):
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".clef-use-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def verify_contract(expected, actual):
    for key in (
        "api_schema_version",
        "schema_sha256",
        "guide_contract_version",
        "operation_registry_version",
    ):
        if key in expected and actual.get(key) != expected[key]:
            raise ValueError(f"installed release contract mismatch: {key}")
    if "guide_bundle_sha256" in expected:
        skills = actual.get("guides", {}).get("skills", {})
        digest = hashlib.sha256(
            json.dumps(skills, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if digest != expected["guide_bundle_sha256"]:
            raise ValueError("installed release contract mismatch: guide bundle")


def smoke(executable, expected_version, contract=None):
    environment = clean_environment()
    version = subprocess.run(
        [str(executable), "version"], capture_output=True, text=True, timeout=30, env=environment
    )
    if version.returncode or version.stdout.strip() != expected_version:
        raise RuntimeError("installed runtime version smoke check failed")
    result = subprocess.run(
        [str(executable), "self-test"], capture_output=True, text=True, timeout=30, env=environment
    )
    if result.returncode:
        raise RuntimeError("installed runtime state-machine smoke check failed")
    if contract and "api_schema_version" in contract:
        discovery = subprocess.run(
            [str(executable), "capabilities", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
        )
        if discovery.returncode:
            raise RuntimeError("installed runtime capability check failed")
        advertised = json.loads(discovery.stdout)
        if advertised.get("runtime_version") != expected_version:
            raise ValueError("installed release runtime version mismatch")
        verify_contract(contract, advertised)


def clean_environment():
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME"):
        environment.pop(name, None)
    return environment


def environment_binary(root, name):
    if sys.platform == "win32":
        return root / "Scripts" / (name + ".exe")
    return root / "bin" / name


@contextlib.contextmanager
def install_lock(path):
    with path.open("a+b") as stream:
        if sys.platform == "win32":
            import msvcrt

            stream.seek(0)
            stream.write(b"0")
            stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream, fcntl.LOCK_EX)
            yield


def windows_existing_user_access(path, sid):
    """Prove an explicit full-control root grant without changing descendant ACLs."""
    import ctypes

    handle, dword = ctypes.c_void_p, ctypes.c_uint32
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.LocalFree.argtypes, kernel.LocalFree.restype = [handle], handle
    signatures = (
        (
            "GetNamedSecurityInfoW",
            [ctypes.c_wchar_p, ctypes.c_int, dword, *([ctypes.POINTER(handle)] * 5)],
            dword,
        ),
        ("ConvertStringSidToSidW", [ctypes.c_wchar_p, ctypes.POINTER(handle)], ctypes.c_int),
        ("GetAce", [handle, dword, ctypes.POINTER(handle)], ctypes.c_int),
        ("EqualSid", [handle, handle], ctypes.c_int),
    )
    for name, arguments, result in signatures:
        function = getattr(security, name)
        function.argtypes, function.restype = arguments, result
    descriptor, acl, user = handle(), handle(), handle()
    try:
        if not security.ConvertStringSidToSidW(sid, ctypes.byref(user)):
            return False
        if (
            security.GetNamedSecurityInfoW(
                str(path), 1, 4, None, None, ctypes.byref(acl), None, ctypes.byref(descriptor)
            )
            or not acl
        ):
            return False
        size = ctypes.c_uint16.from_address(acl.value + 2).value
        count = ctypes.c_uint16.from_address(acl.value + 4).value
        if size < 8 or count > (size - 8) // 4:
            return False
        proven = False
        for index in range(count):
            ace = handle()
            if not security.GetAce(acl, index, ctypes.byref(ace)):
                return False
            if not ace.value or not acl.value + 8 <= ace.value <= acl.value + size - 4:
                return False
            kind = ctypes.c_ubyte.from_address(ace.value).value
            flags = ctypes.c_ubyte.from_address(ace.value + 1).value
            length = ctypes.c_uint16.from_address(ace.value + 2).value
            if kind != 0 or flags & ~0x1F or length < 16 or ace.value + length > acl.value + size:
                return False
            revision = ctypes.c_ubyte.from_address(ace.value + 8).value
            subauthorities = ctypes.c_ubyte.from_address(ace.value + 9).value
            if revision != 1 or subauthorities > 15 or 16 + subauthorities * 4 > length:
                return False
            mask = dword.from_address(ace.value + 4).value
            if flags == 3 and mask == 0x1F01FF and security.EqualSid(ace.value + 8, user):
                proven = True
        return proven
    finally:
        if descriptor:
            kernel.LocalFree(descriptor)
        if user:
            kernel.LocalFree(user)


def windows_user_access(path, *, preserve_existing=False):
    # OpenSSH can create OWNER RIGHTS directories owned by Administrators. The
    # same account's limited desktop token then cannot traverse its installation.
    system = Path(os.environ["SystemRoot"]) / "System32"
    identity = subprocess.run(
        [str(system / "whoami.exe"), "/user", "/fo", "csv", "/nh"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )
    rows = list(csv.reader(identity.stdout.strip().splitlines()))
    if identity.returncode or len(rows) != 1 or len(rows[0]) != 2:
        raise RuntimeError("cannot identify the Windows installation user")
    sid = rows[0][1]
    if not re.fullmatch(r"S-1(?:-\d+){2,14}", sid):
        raise RuntimeError("invalid Windows installation user SID")
    if preserve_existing and windows_existing_user_access(path, sid):
        return
    result = subprocess.run(
        [str(system / "icacls.exe"), str(path), "/grant:r", f"*{sid}:(OI)(CI)F", "/Q"],
        capture_output=True,
        timeout=15,
    )
    if result.returncode:
        raise RuntimeError("cannot grant the installation user access to its private directory")


def install(base_url=DEFAULT_BASE, allow_local=False, progress=None):
    report = progress if progress is not None else lambda message: None
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        raise ValueError("Python 3.11, 3.12 or 3.13 with venv and pip is required")
    base_url = base_url.rstrip("/")
    validate_url(base_url, allow_local)
    windows = sys.platform == "win32"
    default_root = (
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "clef-use"
        if windows
        else Path.home() / ".local/share/clef-use"
    )
    root = Path(os.environ.get("CLEF_USE_INSTALL_ROOT", default_root)).expanduser().absolute()
    bindir = (
        Path(
            os.environ.get(
                "CLEF_USE_BIN_DIR", root / "bin" if windows else Path.home() / ".local/bin"
            )
        )
        .expanduser()
        .absolute()
    )
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    bindir.mkdir(parents=True, exist_ok=True)
    launcher = bindir / ("clef-use.cmd" if windows else "clef-use")
    if launcher.exists() and "clef-use managed launcher" not in launcher.read_text(
        errors="replace"
    ):
        raise ValueError(
            "existing executable belongs to another installation; choose CLEF_USE_BIN_DIR"
        )
    if windows:
        windows_user_access(root, preserve_existing=True)
    with install_lock(root / "install.lock"):
        report("Checking the latest version...")
        raw = fetch(base_url + "/latest/manifest.json", allow_local, 1024 * 1024)
        manifest = parse_manifest(raw, base_url, allow_local)
        artifact = select_artifact(manifest)
        report(
            f"Available version: {manifest['version']} "
            f"(Python {sys.version_info.major}.{sys.version_info.minor})"
        )
        sums = fetch(base_url + "/latest/SHA256SUMS", allow_local, 1024 * 1024).decode()
        if f"{artifact['sha256']}  {artifact['filename']}" not in sums.splitlines():
            raise ValueError("release checksum metadata is inconsistent")
        current = root / "current"
        previous_commands = []
        if windows and launcher.exists():
            current = launcher_target(launcher).parent.parent
        if launcher.exists() and not current.exists():
            raise ValueError(
                "managed launcher belongs to another installation or lacks its release; "
                "choose CLEF_USE_BIN_DIR"
            )
        if current.exists():
            if current.resolve().parent != (root / "versions").resolve():
                raise ValueError(
                    "current runtime belongs to another installation; choose its installation root"
                )
            installed = json.loads((current / "installed.json").read_text())
            old_launcher = installed.get("launcher")
            if not isinstance(old_launcher, str) or not Path(old_launcher).is_absolute():
                raise ValueError("previous installation launcher ownership is unavailable")
            previous_binary = environment_binary(current, "clef-use")
            if launcher.exists() and (
                Path(old_launcher).resolve() != launcher.resolve()
                or launcher_target(launcher).resolve() != previous_binary.resolve()
            ):
                raise ValueError(
                    "managed launcher belongs to another installation; choose CLEF_USE_BIN_DIR"
                )
            # Freeze both the public alias and physical executable before a
            # POSIX current symlink or Windows launcher switches releases.
            previous_commands = list(
                dict.fromkeys(
                    str(path.absolute())
                    for path in (Path(old_launcher), previous_binary, previous_binary.resolve())
                )
            )
            if release_version(installed["version"]) > release_version(manifest["version"]):
                raise ValueError("refusing release downgrade")
            if installed["version"] == manifest["version"]:
                compatible = [
                    item
                    for item in manifest["artifacts"]
                    if (item["platform"], item["architecture"], item["sha256"])
                    == (artifact["platform"], artifact["architecture"], installed["sha256"])
                ]
                if not compatible or not any(
                    f"{item['sha256']}  {item['filename']}" in sums.splitlines()
                    for item in compatible
                ):
                    raise ValueError("immutable release changed checksum")
                report("Checking your existing installation...")
                smoke(environment_binary(current, "clef-use"), installed["version"], artifact)
                return {
                    "status": "CURRENT",
                    "version": installed["version"],
                    "executable": str(launcher),
                    "previous_commands": previous_commands,
                }
            report(f"Updating {installed['version']} -> {manifest['version']}...")
        versions = root / "versions"
        versions.mkdir(exist_ok=True)
        # Venv paths are never renamed; only the activation symlink changes.
        staged = Path(tempfile.mkdtemp(prefix=manifest["version"] + "-", dir=versions))
        activated = False
        launcher_text = None
        try:
            if windows:
                windows_user_access(staged)
            report("Downloading the installation package...")
            payload = fetch(artifact["url"], allow_local)
            report("Verifying the download...")
            verify_checksum(payload, artifact["sha256"])
            with tempfile.TemporaryDirectory(prefix="clef-use-payload-") as temporary:
                temporary = Path(temporary)
                archive = temporary / "release.zip"
                archive.write_bytes(payload)
                safe_extract(archive, temporary / "payload")
                report("Creating an isolated Python environment...")
                # Match python -m venv: copying uv-managed Unix Python breaks its stdlib lookup.
                venv.EnvBuilder(with_pip=True, symlinks=not windows).create(staged)
                package = temporary / "payload"
                report("Installing the runtime and dependencies...")
                result = subprocess.run(
                    [
                        str(environment_binary(staged, "python")),
                        "-m",
                        "pip",
                        "install",
                        "--disable-pip-version-check",
                        "--no-index",
                        "--only-binary=:all:",
                        "--require-hashes",
                        "--find-links",
                        str(package / "wheels"),
                        "-r",
                        str(package / "requirements.txt"),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=clean_environment(),
                )
                if result.returncode:
                    raise RuntimeError(
                        "verified offline wheel installation failed; previous version preserved"
                    )
            report("Checking that clef-use runs correctly...")
            smoke(environment_binary(staged, "clef-use"), manifest["version"], artifact)
            report("Activating the installation...")
            atomic_text(
                staged / "installed.json",
                json.dumps(
                    {
                        "version": manifest["version"],
                        "sha256": artifact["sha256"],
                        "base_url": base_url,
                        "launcher": str(launcher),
                    }
                ),
            )
            if windows:
                if '"' in str(staged) or "%" in str(staged):
                    raise ValueError("Windows installation path contains unsafe CMD expansion")
                executable = environment_binary(staged, "clef-use")
                try:
                    relative = os.path.relpath(executable, bindir)
                except ValueError:
                    relative = None
                # CMD expands the launcher's Unicode directory without decoding it from a file.
                if relative is not None and relative.isascii():
                    target = "%~dp0" + relative
                elif str(executable).isascii():
                    target = str(executable)
                else:
                    raise ValueError(
                        "Unicode Windows paths require CLEF_USE_BIN_DIR inside the installation"
                    )
                launcher_text = '@echo off\nrem clef-use managed launcher\n@"' + target + '" %*\n'
                atomic_text(launcher, launcher_text, 0o755)
            else:
                atomic_text(
                    launcher,
                    "#!/bin/sh\n# clef-use managed launcher\nexec "
                    + shlex.quote(str(current / "bin/clef-use"))
                    + ' "$@"\n',
                    0o755,
                )
                temporary_link = root / ".next"
                temporary_link.unlink(missing_ok=True)
                temporary_link.symlink_to(staged.relative_to(root), target_is_directory=True)
                os.replace(temporary_link, current)
            activated = True
            return {
                "status": "INSTALLED",
                "version": manifest["version"],
                "executable": str(launcher),
                "previous_commands": previous_commands,
                "path_hint": (
                    f"Add {bindir} to PATH if needed. "
                    "Previous versions and model cache are retained."
                ),
            }
        finally:
            if not activated:
                # Ctrl-C can arrive after the atomic switch but before activated is set.
                # Read back the live pointer before deleting an allegedly unused environment.
                activated = (
                    launcher_text is not None
                    and launcher.exists()
                    and launcher.read_text() == launcher_text
                    if windows
                    else current.resolve() == staged.resolve()
                )
            if not activated:
                shutil.rmtree(staged)


def ask_model_preparation():
    if os.environ.get("CLEF_USE_NO_MODEL_PROMPT") == "1" or os.environ.get("CI", "").lower() in {
        "1",
        "true",
    }:
        return None
    input_path, output_path = (
        ("CONIN$", "CONOUT$") if sys.platform == "win32" else ("/dev/tty", "/dev/tty")
    )
    try:
        with (
            open(input_path, encoding="utf-8") as reader,
            open(output_path, "w", encoding="utf-8") as writer,
        ):
            if not reader.isatty():
                return None
            while True:
                writer.write("Prepare models now? [Y/n] ")
                writer.flush()
                answer = reader.readline()
                if not answer:
                    return None
                answer = answer.strip().lower()
                if answer in {"", "y", "yes"}:
                    return True
                if answer in {"n", "no"}:
                    return False
                writer.write("Enter Y or N.\n")
    except (OSError, KeyboardInterrupt):
        return None


def prepare_installed_models(executable, json_mode=False):
    command = [executable, "models", "prepare"]
    if json_mode:
        command.append("--json")
    print(
        "Preparing models..." if not json_mode else "Model preparation requested.",
        file=sys.stderr if json_mode else sys.stdout,
        flush=True,
    )
    try:
        with contextlib.ExitStack() as stack:
            try:
                reader = stack.enter_context(
                    open("CONIN$" if sys.platform == "win32" else "/dev/tty", encoding="utf-8")
                )
            except OSError:
                reader = subprocess.DEVNULL
            completed = subprocess.run(
                command,
                stdin=reader,
                stdout=sys.stderr if json_mode else None,
            )
        if completed.returncode:
            print(
                "Model preparation failed; the runtime is installed. "
                "Resolve the reported error and run clef-use models prepare again.",
                file=sys.stderr,
                flush=True,
            )
            return completed.returncode
    except (OSError, KeyboardInterrupt) as exc:
        print(
            f"Model preparation stopped; the runtime is installed. {type(exc).__name__}",
            file=sys.stderr,
            flush=True,
        )
        return 130 if isinstance(exc, KeyboardInterrupt) else 1
    if not json_mode:
        print("Model preparation complete.", flush=True)
    return 0


def configure_integrations(executable, targets, skills=None, preview_only=False):
    """Only explicit selected harnesses receive new MCP entries and guide copies."""
    reports = {}
    if not targets:
        return reports
    executable = integration_executable(executable)
    for target in targets:
        if target not in {"codex", "hermes", "omp", "all"}:
            raise ValueError("unknown integration target")
        arguments = [
            str(executable),
            "integrate",
            target,
            "--scope",
            "user",
            "--non-interactive",
            "--command-path",
            str(executable),
        ]
        for skill in skills or []:
            if skill not in {"core", "blender", "diagnostics"}:
                raise ValueError("unknown guide selection")
            arguments += ["--skills", skill]
        preview = subprocess.run(
            arguments + ["--dry-run"], capture_output=True, text=True, timeout=60
        )
        if preview.returncode not in (0, 2):
            raise RuntimeError(f"{target} integration preview failed; configuration preserved")
        reports[target] = json.loads(preview.stdout)
        if not preview_only and integrations_ready(reports[target]):
            applied = subprocess.run(arguments, capture_output=True, text=True, timeout=60)
            if applied.returncode not in (0, 2):
                raise RuntimeError(f"{target} integration failed; inspect integrations status")
            reports[target] = json.loads(applied.stdout)
    return reports


def launcher_target(path):
    path = Path(path)
    text = path.read_text()
    if "clef-use managed launcher" not in text:
        raise ValueError("managed launcher ownership marker is missing")
    if path.suffix.lower() != ".cmd":
        commands = [
            shlex.split(line)
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if (
            len(commands) != 1
            or len(commands[0]) != 3
            or commands[0][0] != "exec"
            or commands[0][2] != "$@"
            or not Path(commands[0][1]).is_absolute()
            or text
            != "#!/bin/sh\n# clef-use managed launcher\nexec "
            + shlex.quote(commands[0][1])
            + ' "$@"\n'
        ):
            raise ValueError("managed POSIX launcher is malformed")
        return Path(commands[0][1])
    match = re.fullmatch(r'@echo off\nrem clef-use managed launcher\n@"([^"\r\n]+)" %\*\n', text)
    if not match:
        raise ValueError("managed Windows launcher is malformed")
    target = match[1]
    if target.startswith("%~dp0"):
        target = str(path.parent / target[5:])
    if "%" in target or not Path(target).is_absolute():
        raise ValueError("managed Windows executable path is unsafe")
    return Path(os.path.normpath(target))


def integration_executable(executable):
    path = Path(executable)
    return (
        str(launcher_target(path))
        if sys.platform == "win32" and path.suffix.lower() == ".cmd"
        else str(path)
    )


def integrations_ready(report):
    values = report.get("integrations", [report])
    return all(item.get("status") in {"PREVIEW", "INSTALLED", "UNCHANGED"} for item in values)


def refresh_integrations(result):
    """Refresh approved profiles bound to this installation before activation."""
    previous = result.get("previous_commands")
    if not isinstance(previous, list) or not all(
        isinstance(command, str) and Path(command).is_absolute() for command in previous
    ):
        result["managed_refresh"] = {
            "status": "NOT_RUN",
            "reason": "previous installation ownership unavailable",
        }
        result["integration_status"] = "DEGRADED"
        return result
    if not previous:
        result["managed_refresh"] = {
            "status": "NOT_APPLICABLE",
            "reason": "selected installation has no previous executable",
        }
        return result
    try:
        command = integration_executable(result["executable"])
        refreshed = subprocess.run(
            [
                command,
                "integrations",
                "refresh",
                "--managed-only",
                "--command-path",
                command,
                *[
                    argument
                    for previous_command in previous
                    for argument in ("--previous-command", previous_command)
                ],
            ],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired):
        result["managed_refresh"] = {"status": "NOT_RUN", "reason": "managed refresh unavailable"}
        result["integration_status"] = "DEGRADED"
        return result
    try:
        report = json.loads(refreshed.stdout)
    except (ValueError, TypeError):
        report = {"status": "NOT_RUN", "reason": "managed refresh unavailable"}
    result["managed_refresh"] = report
    if refreshed.returncode or not integrations_ready(report):
        result["integration_status"] = "DEGRADED"
    return result


def main():
    parser = argparse.ArgumentParser(description="Install or update clef-use without root")
    parser.add_argument(
        "--base-url", default=os.environ.get("CLEF_USE_RELEASE_BASE_URL", DEFAULT_BASE)
    )
    parser.add_argument("--allow-insecure-localhost", action="store_true")
    parser.add_argument("--json", action="store_true", help="Emit JSON without progress messages")
    parser.add_argument(
        "--integrate",
        choices=["codex", "hermes", "omp", "all"],
        action="append",
        help="explicitly select MCP and Agent Skill installation targets",
    )
    parser.add_argument("--skills", choices=["core", "blender", "diagnostics"], action="append")
    parser.add_argument(
        "--integration-preview",
        action="store_true",
        help="preview selected integration paths without modifying them",
    )
    models = parser.add_mutually_exclusive_group()
    models.add_argument(
        "--prepare-models",
        dest="prepare_models",
        action="store_true",
        help="prepare models after runtime installation without prompting",
    )
    models.add_argument(
        "--skip-models",
        dest="prepare_models",
        action="store_false",
        help="install the runtime without model preparation or prompting",
    )
    parser.set_defaults(prepare_models=None)
    args = parser.parse_args()

    def progress(message):
        print(f"  {message}", flush=True)

    if not args.json:
        print("clef-use installation\n", flush=True)
    try:
        result = install(
            args.base_url,
            args.allow_insecure_localhost,
            progress=None if args.json else progress,
        )
        result["integrations"] = configure_integrations(
            result["executable"], args.integrate or [], args.skills, args.integration_preview
        )
        if not args.integration_preview:
            refresh_integrations(result)
        result["integration_status"] = (
            "DEGRADED"
            if result.get("integration_status") == "DEGRADED"
            or any(not integrations_ready(item) for item in result["integrations"].values())
            else "SELECTED_TARGETS_APPLIED"
            if result["integrations"]
            else "NO_NEW_TARGETS_SELECTED"
        )
        if args.json:
            print(json.dumps(result))
        else:
            heading = (
                "Already up to date. No installation needed."
                if result["status"] == "CURRENT"
                else "Installation complete."
            )
            print(f"\n{heading}\n  Version: {result['version']}\n  Command: {result['executable']}")
            bindir = str(Path(result["executable"]).parent)
            command = "clef-use"
            if os.path.normcase(bindir) not in {
                os.path.normcase(str(Path(entry).absolute()))
                for entry in os.environ.get("PATH", "").split(os.pathsep)
                if entry
            }:
                command = (
                    f'& "{result["executable"]}"'
                    if sys.platform == "win32"
                    else shlex.quote(result["executable"])
                )
                if sys.platform != "win32":
                    print(
                        "\nTo use clef-use by name in this shell:\n"
                        f'  export PATH={shlex.quote(bindir)}:"$PATH"'
                    )
            print(
                "\nRuntime installation does not download model weights "
                "or install inference dependencies.\n"
                "Before your first GUI task, prepare the models "
                "(Python 3.11/3.12 and Git required).\n"
                "Choose a model cache path with sufficient free space before preparation."
            )
            print(
                f"\nFirst-use setup:\n  {command} models prepare\n  {command} doctor\n"
                f"\nModel setup options:\n  {command} models prepare --help"
            )
            print(
                f"\nAgent setup (MCP plus portable guides):\n"
                f"  {command} integrate codex --dry-run\n"
                f"  {command} integrate codex --scope user\n"
                f"  {command} integrations verify codex --live --read-only"
            )
            if result["integrations"]:
                print(json.dumps(result["integrations"], ensure_ascii=False, indent=2))
        choice = args.prepare_models
        if choice is None and not args.json:
            choice = ask_model_preparation()
        if choice:
            return prepare_installed_models(result["executable"], args.json)
        if not args.json:
            print("Model preparation skipped. Run clef-use models prepare when ready.", flush=True)
    except Exception as exc:
        if args.json:
            print(f"clef-use: {type(exc).__name__}: {exc}", file=sys.stderr)
        else:
            print(
                f"\nInstallation failed.\n  {exc}\n\n"
                "Resolve this error and run the installer again.",
                file=sys.stderr,
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

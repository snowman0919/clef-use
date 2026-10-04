#!/bin/sh
# Generated from src/clef_use/installer.py by scripts/build_installer.py.
set -eu
clef_python="${CLEF_USE_PYTHON:-}"
if [ -z "$clef_python" ]; then
    for candidate in python3.11 python3.12 python3.13 python3; do
        if command -v "$candidate" >/dev/null 2>&1 &&
           "$candidate" -c 'import sys; raise SystemExit(not (3,11) <= sys.version_info[:2] < (3,14))' 2>/dev/null; then
            clef_python="$candidate"
            break
        fi
    done
fi
if [ -z "$clef_python" ]; then
    echo 'clef-use: install Python 3.11-3.13 with venv and pip first' >&2
    exit 2
fi
exec "$clef_python" - "$@" <<'CLEF_USE_INSTALLER_PYTHON'
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


def smoke(executable, expected_version):
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


def windows_user_access(path):
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
    result = subprocess.run(
        [str(system / "icacls.exe"), str(path), "/grant:r", f"*{sid}:(OI)(CI)F", "/Q"],
        capture_output=True,
        timeout=15,
    )
    if result.returncode:
        raise RuntimeError("cannot grant the installation user access to its private directory")


def install(base_url=DEFAULT_BASE, allow_local=False):
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
        windows_user_access(root)
    with install_lock(root / "install.lock"):
        raw = fetch(base_url + "/latest/manifest.json", allow_local, 1024 * 1024)
        manifest = parse_manifest(raw, base_url, allow_local)
        artifact = select_artifact(manifest)
        sums = fetch(base_url + "/latest/SHA256SUMS", allow_local, 1024 * 1024).decode()
        if f"{artifact['sha256']}  {artifact['filename']}" not in sums.splitlines():
            raise ValueError("release checksum metadata is inconsistent")
        current = root / "current"
        if windows and launcher.exists():
            match = re.search(r'^@"([^"\r\n]+)" %\*$', launcher.read_text(), re.MULTILINE)
            if not match:
                raise ValueError("managed Windows launcher is malformed")
            target = match[1]
            if target.startswith("%~dp0"):
                target = os.path.normpath(str(bindir / target[5:]))
            current = Path(target).parent.parent
        if current.exists():
            installed = json.loads((current / "installed.json").read_text())
            if release_version(installed["version"]) > release_version(manifest["version"]):
                raise ValueError("refusing release downgrade")
            if installed["version"] == manifest["version"]:
                if installed["sha256"] != artifact["sha256"]:
                    raise ValueError("immutable release changed checksum")
                smoke(environment_binary(current, "clef-use"), installed["version"])
                return {
                    "status": "CURRENT",
                    "version": installed["version"],
                    "executable": str(launcher),
                }
        versions = root / "versions"
        versions.mkdir(exist_ok=True)
        # Venv paths are never renamed; only the activation symlink changes.
        staged = Path(tempfile.mkdtemp(prefix=manifest["version"] + "-", dir=versions))
        activated = False
        try:
            if windows:
                windows_user_access(staged)
            payload = fetch(artifact["url"], allow_local)
            verify_checksum(payload, artifact["sha256"])
            with tempfile.TemporaryDirectory(prefix="clef-use-payload-") as temporary:
                temporary = Path(temporary)
                archive = temporary / "release.zip"
                archive.write_bytes(payload)
                safe_extract(archive, temporary / "payload")
                venv.EnvBuilder(with_pip=True).create(staged)
                package = temporary / "payload"
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
            smoke(environment_binary(staged, "clef-use"), manifest["version"])
            atomic_text(
                staged / "installed.json",
                json.dumps(
                    {
                        "version": manifest["version"],
                        "sha256": artifact["sha256"],
                        "base_url": base_url,
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
                atomic_text(
                    launcher,
                    '@echo off\nrem clef-use managed launcher\n@"' + target + '" %*\n',
                    0o755,
                )
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
                "path_hint": (
                    f"Add {bindir} to PATH if needed. "
                    "Previous versions and model cache are retained."
                ),
            }
        finally:
            if not activated:
                shutil.rmtree(staged)


def main():
    parser = argparse.ArgumentParser(description="Install or update clef-use without root")
    parser.add_argument(
        "--base-url", default=os.environ.get("CLEF_USE_RELEASE_BASE_URL", DEFAULT_BASE)
    )
    parser.add_argument("--allow-insecure-localhost", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.base_url, args.allow_insecure_localhost)))
    except Exception as exc:
        print(f"clef-use: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

CLEF_USE_INSTALLER_PYTHON

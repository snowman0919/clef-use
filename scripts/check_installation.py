"""Exercise actual packaged installers on loopback, including failed updates."""

from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(site):
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    with tempfile.TemporaryDirectory(prefix="clef-use-install-test-") as temporary:
        root = Path(temporary) / "unicode-\ud55c\uae00 path"
        root.mkdir()
        served = root / "site"
        shutil.copytree(site, served)
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(Quiet, directory=str(served))
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        environment = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
        environment.update(
            CLEF_USE_INSTALL_ROOT=str(root / "installation"),
            CLEF_USE_BIN_DIR=str(root / "bin"),
            CLEF_USE_PYTHON=sys.executable,
            CLEF_USE_NO_PATH_UPDATE="1",
        )
        launcher = root / "bin" / ("clef-use.cmd" if sys.platform == "win32" else "clef-use")
        results = {}

        def invoke(command, success=True):
            result = subprocess.run(
                command, env=environment, cwd=root, capture_output=True, text=True, timeout=360
            )
            if (result.returncode == 0) != success:
                raise AssertionError(
                    f"unexpected installer exit {result.returncode}: {result.stderr}"
                )
            return result

        def publish(manifest):
            for artifact in manifest["artifacts"]:
                artifact["url"] = base + f"/releases/{manifest['version']}/{artifact['filename']}"
            latest = served / "latest"
            (latest / "manifest.json").write_text(json.dumps(manifest))
            (latest / "SHA256SUMS").write_text(
                "".join(f"{a['sha256']}  {a['filename']}\n" for a in manifest["artifacts"])
            )

        try:
            initial = json.loads((served / "latest/manifest.json").read_text())
            publish(initial)
            bootstrap = (
                ["powershell", "-NoProfile", "-File", str(served / "install.ps1")]
                if sys.platform == "win32"
                else ["sh", str(served / "install.sh")]
            )
            first = invoke([*bootstrap, "--base-url", base, "--allow-insecure-localhost"])
            results["first_install"] = json.JSONDecoder().raw_decode(first.stdout.lstrip())[0][
                "status"
            ]
            results["initial_version"] = invoke([str(launcher), "version"]).stdout.strip()
            results["idempotent"] = json.loads(
                invoke(
                    [str(launcher), "update", "--base-url", base, "--allow-insecure-localhost"]
                ).stdout
            )["status"]

            copy = root / "source"
            copy.mkdir()
            for name in ("src", "scripts", "requirements"):
                shutil.copytree(
                    ROOT / name, copy / name, ignore=shutil.ignore_patterns("__pycache__")
                )
            for name in ("pyproject.toml", "README.md", "LICENSE", "THIRD_PARTY_NOTICES.md"):
                shutil.copy2(ROOT / name, copy / name)
            original_version = initial["version"]
            parts = original_version.split(".")
            next_version = ".".join([*parts[:2], str(int(parts[2]) + 1)])
            project = copy / "pyproject.toml"
            project.write_text(
                project.read_text().replace(
                    f'version = "{original_version}"', f'version = "{next_version}"'
                )
            )
            wheels = root / "wheels"
            wheels.mkdir()
            import zipfile

            with zipfile.ZipFile(
                next((served / "releases" / original_version).glob("*.zip"))
            ) as zip:
                for member in zip.namelist():
                    if member.startswith("wheels/") and not member.startswith("wheels/clef_use-"):
                        (wheels / Path(member).name).write_bytes(zip.read(member))
            spec = importlib.util.spec_from_file_location(
                "build_release", ROOT / "scripts/build_release.py"
            )
            builder = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(builder)
            builder.ROOT = copy
            updated = builder.build_release(served, base, wheels)
            results["update"] = json.loads(
                invoke(
                    [str(launcher), "update", "--base-url", base, "--allow-insecure-localhost"]
                ).stdout
            )["status"]
            assert invoke([str(launcher), "version"]).stdout.strip() == next_version
            before = launcher.read_bytes()

            bad = json.loads(json.dumps(updated))
            bad["version"] = ".".join([*parts[:2], str(int(parts[2]) + 2)])
            directory = served / "releases" / bad["version"]
            directory.mkdir()
            artifact = bad["artifacts"][0]
            source = served / "releases" / next_version / artifact["filename"]
            destination = directory / artifact["filename"]
            destination.write_bytes(source.read_bytes() + b"corrupt")
            publish(bad)
            invoke(
                [str(launcher), "update", "--base-url", base, "--allow-insecure-localhost"], False
            )
            results["bad_checksum_preserves_old"] = launcher.read_bytes() == before
            destination.unlink()
            invoke(
                [str(launcher), "update", "--base-url", base, "--allow-insecure-localhost"], False
            )
            results["missing_download_preserves_old"] = launcher.read_bytes() == before
            destination.write_bytes(source.read_bytes())
            artifact["sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
            publish(bad)
            invoke(
                [str(launcher), "update", "--base-url", base, "--allow-insecure-localhost"], False
            )
            results["failed_smoke_preserves_old"] = launcher.read_bytes() == before
            results["final_version"] = invoke([str(launcher), "version"]).stdout.strip()
            assert all(
                results[name]
                for name in (
                    "bad_checksum_preserves_old",
                    "missing_download_preserves_old",
                    "failed_smoke_preserves_old",
                )
            )
            assert results["first_install"] == results["update"] == "INSTALLED"
            assert results["idempotent"] == "CURRENT"
            return results
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check(args.site)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

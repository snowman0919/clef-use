"""Send release update requests in MCP initialization instructions."""

from __future__ import annotations

import queue
import threading

from . import __version__
from .installer import DEFAULT_BASE, fetch, parse_manifest, release_version, select_artifact

STARTUP_TIMEOUT = 3


def update_request(current_version=None):
    current_version = current_version or __version__
    try:
        manifest = parse_manifest(
            fetch(
                DEFAULT_BASE + "/latest/manifest.json", limit=1024 * 1024, timeout=STARTUP_TIMEOUT
            ),
            DEFAULT_BASE,
        )
        if release_version(manifest["version"]) <= release_version(current_version):
            return ""
        select_artifact(manifest)
    except (OSError, ValueError, KeyError, TypeError):
        return ""
    return (
        f"Update requested: clef-use {manifest['version']} is available "
        f"(installed {current_version}). Update with `clef-use update` when permitted "
        "by the user's instructions, then reconnect this MCP server before starting GUI work."
    )


def startup_update_request():
    result = queue.Queue(maxsize=1)

    def check():
        try:
            result.put(update_request())
        except Exception:
            result.put("")

    # DNS and slow HTTP bodies must not hold the stdio handshake indefinitely.
    threading.Thread(target=check, daemon=True).start()
    try:
        return result.get(timeout=STARTUP_TIMEOUT)
    except queue.Empty:
        return ""

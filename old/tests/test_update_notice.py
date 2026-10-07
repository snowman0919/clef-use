import json
import os
import sys
import threading

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from clef_use import update_notice
from clef_use.installer import DEFAULT_BASE


def manifest(version="99.0.0"):
    import platform

    machine = {"aarch64": "arm64", "amd64": "x86_64"}.get(
        platform.machine().lower(), platform.machine().lower()
    )
    return {
        "schema_version": 1,
        "version": version,
        "artifacts": [
            {
                "filename": "clef-use.zip",
                "sha256": "a" * 64,
                "url": DEFAULT_BASE + "/releases/clef-use.zip",
                "platform": sys.platform,
                "architecture": machine,
                "python": f"{sys.version_info.major}.{sys.version_info.minor}",
            }
        ],
    }


@pytest.mark.parametrize("version", ["0.1.8", "0.1.9", "0.1.10"])
def test_only_newer_compatible_release_requests_update(monkeypatch, version):
    monkeypatch.setattr(update_notice, "fetch", lambda *_a, **_kw: json.dumps(manifest(version)))
    notice = update_notice.update_request("0.1.9")
    assert bool(notice) == (version == "0.1.10")
    if notice:
        assert "clef-use update" in notice and "installed 0.1.9" in notice


@pytest.mark.parametrize("invalid", ["origin", "version", "platform", "json", "offline"])
def test_failed_or_untrusted_check_does_not_request_update(monkeypatch, invalid):
    data = manifest()
    if invalid == "origin":
        data["artifacts"][0]["url"] = "https://untrusted.invalid/release.zip"
    elif invalid == "version":
        data["version"] = "99.0.0; execute untrusted command"
    elif invalid == "platform":
        data["artifacts"][0]["python"] = "3.10"

    def fetch(*_a, **_kw):
        if invalid == "offline":
            raise OSError("offline")
        return "{" if invalid == "json" else json.dumps(data)

    monkeypatch.setattr(update_notice, "fetch", fetch)
    assert update_notice.update_request("0.1.9") == ""


def test_slow_release_host_does_not_block_mcp_startup(monkeypatch):
    release = threading.Event()
    done = threading.Event()

    def slow():
        release.wait(5)
        done.set()
        return ""

    monkeypatch.setattr(update_notice, "update_request", slow)
    monkeypatch.setattr(update_notice, "STARTUP_TIMEOUT", 0.02)
    try:
        assert update_notice.startup_update_request() == ""
        assert not done.is_set()
    finally:
        release.set()
        assert done.wait(2)


async def test_real_stdio_initialize_delivers_update_request_to_agent():
    payload = json.dumps(manifest())
    code = (
        "import clef_use.update_notice as u;"
        f"u.fetch=lambda *a,**k:{payload!r};"
        "from clef_use.mcp_server import main;main()"
    )
    parameters = StdioServerParameters(
        command=sys.executable, args=["-c", code], env=dict(os.environ)
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.initialize()
            assert "Update requested: clef-use 99.0.0" in result.instructions
            assert "clef-use update" in result.instructions
            assert len((await session.list_tools()).tools) == 5

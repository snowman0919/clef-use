"""Exercise the actual guardian loop against a stateful, pure Windows boundary."""

import json
import sys
import threading
import time
from types import ModuleType, SimpleNamespace

import pytest

from clef_use import input_ir


def recover_then_eof(monkeypatch, entries, fail_once=()):
    """Another owner acquires successfully released inputs before parent EOF."""
    recovered = threading.Event()
    held = {entry: "agent" for entry in entries}
    pending_failures = set(fail_once)
    attempts = []
    stale_releases = []
    feed_timeout = []

    class NativeBoundary:
        def _send(self, event):
            keyboard = event.keyboard
            entry = ("unicode" if keyboard.flags & 4 else "key", keyboard.scan)
            attempts.append(entry)
            try:
                if entry in pending_failures:
                    pending_failures.remove(entry)
                    raise RuntimeError("native release refused before acknowledgement")
                if held.get(entry) == "other":
                    stale_releases.append(entry)
                held.pop(entry, None)
            finally:
                if len(attempts) == len(entries):
                    recovered.set()

    class Feed:
        def __iter__(self):
            keys = {str(scan): [0, scan, 8] for kind, scan in entries if kind == "key"}
            yield (
                json.dumps(
                    {
                        "owned": [["key", key] for key in keys],
                        "deadline": time.monotonic() - 1,
                        "native_keys": keys,
                        "unicode_units": [scan for kind, scan in entries if kind == "unicode"],
                    }
                )
                + "\n"
            )
            if not recovered.wait(1):
                feed_timeout.append(True)
                return
            for entry in entries:
                if entry not in held:
                    held[entry] = "other"
            # End the input stream only after the first recovery completed.

    native = ModuleType("clef_use.windows_input")
    native.WindowsInput = NativeBoundary
    native.Input = lambda **fields: SimpleNamespace(**fields)
    native.KeyboardInput = lambda vk, scan, flags, time, extra: SimpleNamespace(
        vk=vk, scan=scan, flags=flags, time=time, extra=extra
    )
    with monkeypatch.context() as isolated:
        isolated.setitem(sys.modules, "clef_use.windows_input", native)
        isolated.setattr(input_ir, "sys", SimpleNamespace(platform="win32", stdin=Feed()))
        input_ir._guardian_main()
    assert not feed_timeout, "guardian failed to process the expired lease"
    return held, attempts, stale_releases


@pytest.mark.parametrize("entry", [("key", 29), ("unicode", 65)])
def test_deadline_recovery_does_not_release_a_new_owner_on_later_eof(monkeypatch, entry):
    held, attempts, stale_releases = recover_then_eof(monkeypatch, [entry])
    assert held == {entry: "other"}
    assert stale_releases == []
    assert attempts == [entry]


@pytest.mark.parametrize("failed", [("key", 29), ("unicode", 65)])
def test_failed_recovery_remains_pending_without_replaying_successes(monkeypatch, failed):
    entries = [("key", 29), ("key", 42), ("unicode", 65)]
    held, attempts, stale_releases = recover_then_eof(monkeypatch, entries, [failed])
    assert failed not in held
    assert held == {entry: "other" for entry in entries if entry != failed}
    assert stale_releases == []
    assert attempts.count(failed) == 2
    assert all(attempts.count(entry) == 1 for entry in entries if entry != failed)

"""Explicit X11 text clipboard transfer, with native INCR read acknowledgement.

ICCCM selection/INCR protocol:
https://xorg.freedesktop.org/archive/X11R7.7/doc/xorg-docs/icccm/icccm.html
Only the focused application's verified X-Resource client can acknowledge a
transfer. This proves native data consumption, not a widget effect. After a
possibly delivered paste, cancellation/parent EOF retains offered data until
consumption or another owner; restoring old data early could paste wrong text.
The private process persists restored text like xsel until ownership changes.
"""

import json
import math
import queue
import select
import subprocess
import sys
import threading
import time

_ownership_acquired = False


class ClipboardTransferError(RuntimeError):
    pass


class X11ClipboardTransfer:
    def __init__(self, text, display_name, deadline, cancelled, check):
        self.deadline, self.cancelled, self.check = deadline, cancelled, check
        self.armed = False
        self.consumed = False
        self.offered = False
        self.restored = False
        self.owner_changed = False
        self.closed = False
        self.events = queue.Queue()
        self.process = subprocess.Popen(
            [sys.executable, "-m", "clef_use.x11_clipboard"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            close_fds=True,
        )

        def read():
            try:
                for line in self.process.stdout:
                    try:
                        self.events.put(json.loads(line))
                    except ValueError:
                        continue  # Xlib may emit an Xauthority diagnostic.
            finally:
                self.events.put({"event": "closed"})

        threading.Thread(target=read, daemon=True).start()
        try:
            self._send({"text": text, "display": display_name, "deadline": deadline})
            self.offered = True  # Possible takeover until native status is observed.
            self._await("ready")
            self.offered = True
        except BaseException as exc:
            self.close()
            if self.unresolved:
                raise ClipboardTransferError(
                    f"{exc}; clipboard restoration unacknowledged"
                ) from exc
            raise

    def _send(self, message):
        try:
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()
        except (OSError, ValueError) as exc:
            raise ClipboardTransferError("X11 clipboard provider disconnected") from exc

    def _await(self, wanted):
        while True:
            try:
                self.check()
                if self.cancelled.is_set() or time.monotonic() >= self.deadline:
                    raise ClipboardTransferError("clipboard transfer cancelled or deadline expired")
                message = self.events.get_nowait()
            except queue.Empty:
                self.cancelled.wait(0.01)
                continue
            event = message["event"]
            if event == "owner_changed":
                self.owner_changed = True
            if event == "error" and not message.get("ownership_acquired", True):
                self.offered = False
            if event == wanted:
                return
            if event in {"error", "closed", "owner_changed"}:
                raise ClipboardTransferError(
                    message.get("reason", "clipboard owner or provider changed")
                )

    def arm(self):
        self.armed = True
        self._send({"arm": True})
        self._await("armed")

    def wait_consumed(self):
        self._await("consumed")
        self.consumed = True

    def cancel_before_trigger(self, *, deadline: float) -> None:
        """Terminal recovery only when the caller knows no paste was attempted.

        Cancellation and target guards cannot block owned recovery. The caller
        supplies its explicit cleanup deadline, independently of an expired
        input deadline. Only a native restoration or new-owner ACK resolves
        ownership; EOF alone remains conservative after arming.
        """
        try:
            if self.restored or self.owner_changed or self.consumed:
                self.armed = False
                return
            if self.closed:
                raise ClipboardTransferError("clipboard recovery command pipe already closed")
            if not math.isfinite(deadline):
                raise ClipboardTransferError("clipboard recovery deadline invalid")
            self._send({"cancel_before_trigger": True})
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ClipboardTransferError(
                        "clipboard recovery acknowledgement deadline expired"
                    )
                try:
                    message = self.events.get(timeout=remaining)
                except queue.Empty as exc:
                    raise ClipboardTransferError(
                        "clipboard recovery acknowledgement deadline expired"
                    ) from exc
                event = message["event"]
                if event == "restored":
                    self.restored = True
                    self.armed = False
                    return
                if event == "owner_changed":
                    self.owner_changed = True
                    self.armed = False
                    return
                if event == "error" and not message.get("ownership_acquired", True):
                    self.offered = False
                if event in {"error", "closed"}:
                    raise ClipboardTransferError(
                        message.get("reason", "clipboard provider closed before recovery ACK")
                    )
        finally:
            # Do not let the later idempotent close add another input-deadline
            # wait after this explicitly bounded cleanup attempt.
            self.closed = True
            if self.process.stdin and not self.process.stdin.closed:
                try:
                    self.process.stdin.close()
                except (OSError, ValueError):
                    pass

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        if self.offered and not self.armed:
            # Before any possibly delivered paste, restoration is safe, but
            # still requires an actual provider acknowledgement.
            while time.monotonic() < self.deadline:
                try:
                    message = self.events.get(
                        timeout=min(0.01, max(0, self.deadline - time.monotonic()))
                    )
                except queue.Empty:
                    continue
                event = message["event"]
                if event == "restored":
                    self.restored = True
                    return
                if event == "error" and not message.get("ownership_acquired", True):
                    self.offered = False
                if event in {"owner_changed", "closed", "error"}:
                    self.owner_changed = event == "owner_changed"
                    return

    @property
    def unresolved(self):
        return self.offered and not (self.consumed or self.restored or self.owner_changed)


def _provider():
    global _ownership_acquired
    from Xlib import X, Xatom, display, error, protocol
    from Xlib.protocol import rq

    # python-xlib does not provide X-Resource. Wire layout is XResproto.h,
    # XResQueryClients (extension opcode 1), with native resource base/masks.
    class QueryClients(rq.ReplyRequest):
        _request = rq.Struct(rq.Card8("opcode"), rq.Opcode(1), rq.RequestLength())
        _reply = rq.Struct(
            rq.ReplyCode(),
            rq.Pad(1),
            rq.Card16("sequence_number"),
            rq.ReplyLength(),
            rq.LengthOf("clients", 4),
            rq.Pad(20),
            rq.List("clients", rq.Struct(rq.Card32("resource_base"), rq.Card32("resource_mask"))),
        )

    def emit(event, **kwargs):
        try:
            print(json.dumps({"event": event, **kwargs}), flush=True)
        except (BrokenPipeError, OSError):
            pass

    setup = json.loads(sys.stdin.readline())
    commands = queue.Queue()

    def read():
        for line in sys.stdin:
            commands.put(json.loads(line))
        commands.put(None)

    # EOF must interrupt a pending snapshot before any selection takeover.
    threading.Thread(target=read, daemon=True).start()

    def before_takeover():
        try:
            command = commands.get_nowait()
        except queue.Empty:
            return
        if command is None:
            raise ClipboardTransferError("clipboard setup cancelled before takeover")
        raise ClipboardTransferError("unexpected clipboard setup command")

    before_takeover()
    c = display.Display(setup["display"])
    w = c.screen().root.create_window(
        0, 0, 1, 1, 0, X.CopyFromParent, event_mask=X.PropertyChangeMask
    )
    # A timestamp taken before snapshotting prevents a later ownership change
    # from being overwritten by this acquisition. X timestamps have millisecond
    # granularity; this is native ordering, not a strict compare-and-swap.
    stamp_atom = c.intern_atom("_CLEF_SELECTION_TIMESTAMP")
    w.change_property(stamp_atom, Xatom.INTEGER, 32, [1])
    c.flush()
    acquisition_time = None
    while time.monotonic() < setup["deadline"] and acquisition_time is None:
        before_takeover()
        if not c.pending_events():
            select.select([c], [], [], 0.01)
            continue
        event = c.next_event()
        if event.type == X.PropertyNotify and event.atom == stamp_atom:
            acquisition_time = event.time
    if acquisition_time is None:
        raise ClipboardTransferError("clipboard acquisition timestamp unavailable")
    clip, targets, utf8, incr, timestamp, multiple, atom_pair = [
        c.intern_atom(n)
        for n in (
            "CLIPBOARD",
            "TARGETS",
            "UTF8_STRING",
            "INCR",
            "TIMESTAMP",
            "MULTIPLE",
            "ATOM_PAIR",
        )
    ]
    extension = c.query_extension("X-Resource")
    if not extension or not extension.present:
        raise ClipboardTransferError("native clipboard requestor identity requires X-Resource")
    clients = QueryClients(display=c.display, opcode=extension.major_opcode).clients
    focus = c.get_input_focus().focus
    if not hasattr(focus, "id"):
        raise ClipboardTransferError("clipboard target input focus unknown")
    identities = [
        (v.resource_base, v.resource_mask)
        for v in clients
        if focus.id & ~v.resource_mask == v.resource_base and v.resource_base
    ]
    if len(identities) != 1:
        raise ClipboardTransferError("clipboard target native client identity unknown")
    base, mask = identities[0]
    previous_owner = c.get_selection_owner(clip)
    previous_id = previous_owner.id if hasattr(previous_owner, "id") else previous_owner
    snapshot_atom = c.intern_atom("_CLEF_TEXT_SNAPSHOT")
    snapshot_limit = 1024 * 1024

    def native_bytes(value):
        # python-xlib decodes valid UTF-8 PropertyData to str. Reverse that
        # decoding before preserving the bytes, regardless of the target atom.
        return value.encode("utf-8") if isinstance(value, str) else bytes(value)

    def fetch(target):
        w.convert_selection(clip, target, snapshot_atom, X.CurrentTime)
        c.flush()
        chunks, actual_type, actual_format, incremental = [], None, None, False
        while time.monotonic() < setup["deadline"]:
            before_takeover()
            if not c.pending_events():
                select.select([c], [], [], min(0.01, max(0, setup["deadline"] - time.monotonic())))
                continue
            e = c.next_event()
            if e.type == X.SelectionNotify:
                if e.property == X.NONE:
                    raise ClipboardTransferError("previous clipboard format cannot be restored")
                value = w.get_property(
                    snapshot_atom, X.AnyPropertyType, 0, snapshot_limit // 4 + 1, delete=True
                )
                if value is None or value.bytes_after:
                    raise ClipboardTransferError("previous clipboard exceeds bounded text snapshot")
                if value.property_type == incr:
                    incremental = True
                    c.flush()
                    continue
                data = native_bytes(value.value) if value.format == 8 else value.value
                return value.property_type, value.format, data
            if (
                incremental
                and e.type == X.PropertyNotify
                and e.atom == snapshot_atom
                and e.state == X.PropertyNewValue
            ):
                value = w.get_property(
                    snapshot_atom, X.AnyPropertyType, 0, snapshot_limit // 4 + 1, delete=True
                )
                c.flush()
                if value is None or value.bytes_after or value.format != 8:
                    raise ClipboardTransferError(
                        "previous clipboard incremental format unsupported"
                    )
                actual_type, actual_format = value.property_type, value.format
                if not len(value.value):
                    return actual_type, actual_format, b"".join(chunks)
                chunks.append(native_bytes(value.value))
                if sum(map(len, chunks)) > snapshot_limit:
                    raise ClipboardTransferError("previous clipboard exceeds bounded text snapshot")
        raise ClipboardTransferError("previous clipboard snapshot deadline expired")

    previous = {}
    if previous_id:
        kind, form, advertised = fetch(targets)
        if kind != Xatom.ATOM or form != 32:
            raise ClipboardTransferError("previous clipboard TARGETS unavailable")
        metadata = {"TARGETS", "TIMESTAMP", "MULTIPLE", "SAVE_TARGETS", "DELETE", "INCR"}
        text_names = {
            "UTF8_STRING",
            "STRING",
            "TEXT",
            "COMPOUND_TEXT",
            "text/plain",
            "text/plain;charset=utf-8",
            "text/plain;charset=UTF-8",
        }
        for atom in advertised:
            name = c.get_atom_name(atom)
            if name in metadata:
                continue
            if name not in text_names:
                raise ClipboardTransferError("clipboard format restoration unsupported")
            previous[atom] = fetch(atom)
            if previous[atom][1] != 8:
                raise ClipboardTransferError("previous clipboard text encoding unsupported")
        if not previous:
            raise ClipboardTransferError("previous clipboard has no restorable text format")
    else:
        previous[utf8] = (utf8, 8, b"")
    owner = c.get_selection_owner(clip)
    if (owner.id if hasattr(owner, "id") else owner) != previous_id:
        raise ClipboardTransferError("clipboard owner changed during snapshot")
    offered = {utf8: (utf8, 8, setup["text"].encode("utf-8"))}
    text_atom = c.intern_atom("TEXT")
    offered[text_atom] = offered[utf8]
    try:
        offered[Xatom.STRING] = (Xatom.STRING, 8, setup["text"].encode("latin-1"))
    except UnicodeEncodeError:
        pass
    current = offered
    before_takeover()
    # A connection failure after this request cannot prove either ownership or
    # restoration. Clear this conservative status only on an observed refusal.
    _ownership_acquired = True
    w.set_selection_owner(clip, acquisition_time)
    c.sync()
    owner = c.get_selection_owner(clip)
    if not hasattr(owner, "id") or owner.id != w.id:
        _ownership_acquired = False
        raise ClipboardTransferError("clipboard ownership refused")
    emit("ready")
    armed = False
    restored = False
    owner_lost = False
    transfers = {}

    def restore():
        nonlocal current, restored
        # Do not reacquire ownership: a concurrent copy must always win. The
        # same private owner switches only its served snapshot, so no old data
        # can replace a new owner's selection even across a scheduling race.
        owner = c.get_selection_owner(clip)
        if hasattr(owner, "id") and owner.id == w.id:
            current = previous
            restored = True
            return True
        return False

    def discard_requestor(window_id):
        for key in tuple(transfers):
            if key[0] == window_id:
                del transfers[key]

    def request_error(requestor, prop):
        def handle(native_error, request):
            if isinstance(native_error, error.BadWindow):
                discard_requestor(requestor.id)
                return 1
            if isinstance(native_error, error.BadAtom):
                transfers.pop((requestor.id, prop), None)
                return 1
            return 0

        return handle

    def change_property(requestor, prop, data_type, data_format, data):
        caught = error.CatchError(error.BadWindow, error.BadAtom)
        requestor.change_property(prop, data_type, data_format, data, onerror=caught)
        c.sync()
        failed = caught.get_error()
        if failed is not None:
            request_error(requestor, prop)(failed, caught.get_request())
            return False
        return True

    def convert(requestor, target, prop):
        if owner_lost or prop == X.NONE or (requestor.id, prop) in transfers:
            return False
        if target == targets:
            return change_property(
                requestor, prop, Xatom.ATOM, 32, [targets, multiple, timestamp, *current]
            )
        elif target == timestamp:
            return change_property(requestor, prop, Xatom.INTEGER, 32, [acquisition_time])
        elif target in current:
            data_type, data_format, data = current[target]
            if not restored or len(data) > 16384:
                caught = error.CatchError(error.BadWindow)
                requestor.change_attributes(
                    event_mask=X.PropertyChangeMask | X.StructureNotifyMask, onerror=caught
                )
                c.sync()
                if caught.get_error() is not None:
                    discard_requestor(requestor.id)
                    return False
                if not change_property(requestor, prop, incr, 32, [len(data)]):
                    return False
                intended = armed and requestor.id & ~mask == base
                transfers[(requestor.id, prop)] = [
                    requestor,
                    data_type,
                    data_format,
                    data,
                    0,
                    False,
                    intended,
                ]
            else:
                return change_property(requestor, prop, data_type, data_format, data)
        else:
            return False
        return True

    while True:
        try:
            command = commands.get_nowait()
        except queue.Empty:
            command = {}
        if command is None:
            if not armed:
                if restore():
                    emit("restored")
            # After possible OS delivery, EOF keeps offered data available for
            # the queued paste; there is no safe time-based restoration.
        elif command.get("arm"):
            armed = True
            emit("armed")
        elif command.get("cancel_before_trigger"):
            # This authority comes only from the local caller's positive
            # knowledge that the paste trigger has never been attempted.
            if restore():
                armed = False
                emit("restored")
            else:
                owner_lost = True
                emit("owner_changed")
        while c.pending_events():
            e = c.next_event()
            if e.type == X.SelectionClear:
                owner_lost = True
                emit("owner_changed")
            elif e.type == X.DestroyNotify:
                # Native destruction ends the requestor's handshake; other
                # live transfers still finish after selection ownership ends.
                discard_requestor(e.window.id)
            elif e.type == X.SelectionRequest:
                prop = e.property or e.target
                if owner_lost or e.selection != clip:
                    prop = X.NONE
                elif e.target == multiple:
                    # At most 64 pairs; nested and side-effect targets fail
                    # independently without recursively interpreting requests.
                    try:
                        pairs = (
                            e.requestor.get_property(prop, atom_pair, 0, 129)
                            if e.property
                            else None
                        )
                    except (error.BadWindow, error.BadAtom) as exc:
                        request_error(e.requestor, prop)(exc, None)
                        pairs = None
                    if (
                        pairs is None
                        or pairs.property_type != atom_pair
                        or pairs.format != 32
                        or pairs.bytes_after
                        or len(pairs.value) > 128
                        or len(pairs.value) % 2
                    ):
                        prop = X.NONE
                    else:
                        values = list(pairs.value)
                        used = {prop}
                        for index in range(0, len(values), 2):
                            target, destination = values[index : index + 2]
                            if (
                                destination in used
                                or target == multiple
                                or not convert(e.requestor, target, destination)
                            ):
                                values[index] = X.NONE
                            else:
                                used.add(destination)
                        if not change_property(e.requestor, prop, atom_pair, 32, values):
                            prop = X.NONE
                elif not convert(e.requestor, e.target, prop):
                    prop = X.NONE
                e.requestor.send_event(
                    protocol.event.SelectionNotify(
                        time=e.time,
                        requestor=e.requestor,
                        selection=e.selection,
                        target=e.target,
                        property=prop,
                    ),
                    propagate=False,
                    onerror=request_error(e.requestor, prop),
                )
                c.flush()
            elif e.type == X.PropertyNotify and e.state == X.PropertyDelete:
                key = (e.window.id, e.atom)
                transfer = transfers.get(key)
                if transfer is None:
                    continue
                requestor, data_type, data_format, data, offset, ended, intended = transfer
                if ended:
                    del transfers[key]
                    if intended and not restored:
                        restore()
                        emit("consumed")
                elif offset < len(data):
                    chunk = data[offset : offset + 16384]
                    requestor.change_property(
                        e.atom,
                        data_type,
                        data_format,
                        chunk,
                        onerror=request_error(requestor, e.atom),
                    )
                    transfer[4] += len(chunk)
                else:
                    requestor.change_property(
                        e.atom,
                        data_type,
                        data_format,
                        b"",
                        onerror=request_error(requestor, e.atom),
                    )
                    transfer[5] = True
                c.flush()
        if owner_lost and not transfers:
            c.close()
            return
        select.select([c], [], [], 0.01)


if __name__ == "__main__":
    try:
        _provider()
    except Exception as exc:
        print(
            json.dumps(
                {"event": "error", "reason": str(exc), "ownership_acquired": _ownership_acquired}
            ),
            flush=True,
        )

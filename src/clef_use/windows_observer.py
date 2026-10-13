"""Native identities and private rendezvous files for local Blender observation."""

from __future__ import annotations

import ctypes
import os
import socket
from contextlib import contextmanager
from functools import lru_cache

from .windows_input import Point, Rect

DWORD = ctypes.c_uint32
HANDLE = ctypes.c_void_p


class SecurityAttributes(ctypes.Structure):
    _fields_ = [("length", DWORD), ("descriptor", HANDLE), ("inherit", ctypes.c_int)]


class Acl(ctypes.Structure):
    _fields_ = [
        ("revision", ctypes.c_ubyte),
        ("reserved", ctypes.c_ubyte),
        ("size", ctypes.c_uint16),
        ("count", ctypes.c_uint16),
        ("reserved2", ctypes.c_uint16),
    ]


class TcpRow(ctypes.Structure):
    _fields_ = [
        (name, DWORD)
        for name in ("state", "local_addr", "local_port", "remote_addr", "remote_port", "pid")
    ]


@lru_cache(maxsize=1)
def api():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    network = ctypes.WinDLL("iphlpapi", use_last_error=True)
    signatures = (
        (kernel, "OpenProcess", [DWORD, ctypes.c_int, DWORD], HANDLE),
        (kernel, "CloseHandle", [HANDLE], ctypes.c_int),
        (kernel, "LocalFree", [HANDLE], HANDLE),
        (
            kernel,
            "CreateFileW",
            [
                ctypes.c_wchar_p,
                DWORD,
                DWORD,
                ctypes.POINTER(SecurityAttributes),
                DWORD,
                DWORD,
                HANDLE,
            ],
            HANDLE,
        ),
        (kernel, "WriteFile", [HANDLE, HANDLE, DWORD, ctypes.POINTER(DWORD), HANDLE], ctypes.c_int),
        (
            kernel,
            "CreateDirectoryW",
            [ctypes.c_wchar_p, ctypes.POINTER(SecurityAttributes)],
            ctypes.c_int,
        ),
        (security, "OpenProcessToken", [HANDLE, DWORD, ctypes.POINTER(HANDLE)], ctypes.c_int),
        (
            security,
            "GetTokenInformation",
            [HANDLE, ctypes.c_int, HANDLE, DWORD, ctypes.POINTER(DWORD)],
            ctypes.c_int,
        ),
        (security, "ConvertSidToStringSidW", [HANDLE, ctypes.POINTER(HANDLE)], ctypes.c_int),
        (
            security,
            "ConvertStringSecurityDescriptorToSecurityDescriptorW",
            [ctypes.c_wchar_p, DWORD, ctypes.POINTER(HANDLE), ctypes.POINTER(DWORD)],
            ctypes.c_int,
        ),
        (
            security,
            "GetNamedSecurityInfoW",
            [
                ctypes.c_wchar_p,
                ctypes.c_int,
                DWORD,
                ctypes.POINTER(HANDLE),
                ctypes.POINTER(HANDLE),
                ctypes.POINTER(HANDLE),
                ctypes.POINTER(HANDLE),
                ctypes.POINTER(HANDLE),
            ],
            DWORD,
        ),
        (security, "GetAce", [HANDLE, DWORD, ctypes.POINTER(HANDLE)], ctypes.c_int),
        (
            network,
            "GetExtendedTcpTable",
            [HANDLE, ctypes.POINTER(DWORD), ctypes.c_int, DWORD, DWORD, DWORD],
            DWORD,
        ),
    )
    for library, name, arguments, result in signatures:
        function = getattr(library, name)
        function.argtypes, function.restype = arguments, result
    return kernel, security, network


def sid_string(sid):
    kernel, security, _ = api()
    value = HANDLE()
    if not security.ConvertSidToStringSidW(sid, ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.wstring_at(value)
    finally:
        kernel.LocalFree(value)


def process_user(pid):
    kernel, security, _ = api()
    process = kernel.OpenProcess(0x1000, False, pid)
    if not process:
        raise ctypes.WinError(ctypes.get_last_error())
    token = HANDLE()
    try:
        if not security.OpenProcessToken(process, 8, ctypes.byref(token)):
            raise ctypes.WinError(ctypes.get_last_error())
        size = DWORD()
        security.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not 0 < size.value <= 65536:
            raise ValueError("observer process token size unavailable")
        buffer = ctypes.create_string_buffer(size.value)
        if not security.GetTokenInformation(token, 1, buffer, size.value, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        # TOKEN_USER begins with SID_AND_ATTRIBUTES; its first member is PSID.
        return sid_string(HANDLE.from_buffer(buffer).value)
    finally:
        if token:
            kernel.CloseHandle(token)
        kernel.CloseHandle(process)


@contextmanager
def private_security_attributes():
    kernel, security, _ = api()
    user = process_user(os.getpid())
    descriptor, size = HANDLE(), DWORD()
    sddl = f"O:{user}D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FA;;;{user})"
    if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, 1, ctypes.byref(descriptor), ctypes.byref(size)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield SecurityAttributes(ctypes.sizeof(SecurityAttributes), descriptor, False)
    finally:
        kernel.LocalFree(descriptor)


def create_private_directory(path):
    kernel, _, _ = api()
    with private_security_attributes() as attributes:
        if not kernel.CreateDirectoryW(str(path), ctypes.byref(attributes)):
            error = ctypes.get_last_error()
            if error in (80, 183):
                raise FileExistsError("observer directory already exists")
            raise ctypes.WinError(error)


def write_private_metadata(path, data):
    kernel, _, _ = api()
    if len(data) > 512:
        raise ValueError("observer endpoint metadata exceeds limit")
    with private_security_attributes() as attributes:
        handle = kernel.CreateFileW(
            str(path), 0x40000000, 1, ctypes.byref(attributes), 1, 128, None
        )
        if handle == HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        identity, complete = None, False
        try:
            identity = path.lstat().st_ino
            written = DWORD()
            if not kernel.WriteFile(
                handle, ctypes.c_char_p(data), len(data), ctypes.byref(written), None
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            if written.value != len(data):
                raise OSError("observer endpoint write incomplete")
            complete = True
        finally:
            kernel.CloseHandle(handle)
            if not complete and identity is not None:
                try:
                    if path.lstat().st_ino == identity:
                        path.unlink()
                except FileNotFoundError:
                    pass


def private_path(path):
    """Reject foreign owners, null/unsupported ACLs and grants to other users."""
    kernel, security, _ = api()
    owner, acl, descriptor = HANDLE(), HANDLE(), HANDLE()
    error = security.GetNamedSecurityInfoW(
        str(path),
        1,
        5,
        ctypes.byref(owner),
        None,
        ctypes.byref(acl),
        None,
        ctypes.byref(descriptor),
    )
    if error:
        raise ctypes.WinError(error)
    try:
        user = process_user(os.getpid())
        if not owner or sid_string(owner) != user or not acl:
            raise ValueError("observer path ownership or permissions mismatch")
        header = ctypes.cast(acl, ctypes.POINTER(Acl)).contents
        own_access = False
        for index in range(header.count):
            ace = HANDLE()
            if not security.GetAce(acl, index, ctypes.byref(ace)):
                raise ctypes.WinError(ctypes.get_last_error())
            kind = ctypes.c_ubyte.from_address(ace.value).value
            flags = ctypes.c_ubyte.from_address(ace.value + 1).value
            length = ctypes.c_uint16.from_address(ace.value + 2).value
            if kind != 0 or length < 12:
                raise ValueError("observer path ACL unsupported")
            granted = sid_string(ace.value + 8)
            mask = DWORD.from_address(ace.value + 4).value
            if granted not in {user, "S-1-5-18", "S-1-5-32-544"}:
                raise ValueError("observer path grants another principal access")
            if granted == user and not flags & 8 and mask & 0x1F01FF == 0x1F01FF:
                own_access = True
        if not own_access:
            raise ValueError("observer owner access unavailable")
    finally:
        kernel.LocalFree(descriptor)


def peer_credentials(connection):
    local, remote = connection.getsockname(), connection.getpeername()
    if connection.family != socket.AF_INET or local[0] != "127.0.0.1" or remote[0] != "127.0.0.1":
        raise ValueError("observer connection is not IPv4 loopback")
    _, _, network = api()
    size = DWORD()
    result = network.GetExtendedTcpTable(None, ctypes.byref(size), False, 2, 5, 0)
    if result not in (0, 122) or not 4 <= size.value <= 2 * 1024 * 1024:
        raise ValueError("observer native TCP table unavailable")
    buffer = ctypes.create_string_buffer(size.value)
    result = network.GetExtendedTcpTable(buffer, ctypes.byref(size), False, 2, 5, 0)
    if result:
        raise ctypes.WinError(result)
    count = DWORD.from_buffer(buffer).value
    if 4 + count * ctypes.sizeof(TcpRow) > len(buffer):
        raise ValueError("observer native TCP table malformed")
    rows = (TcpRow * count).from_buffer(buffer, 4)
    loopback = int.from_bytes(socket.inet_aton("127.0.0.1"), "little")
    matches = [
        row.pid
        for row in rows
        if row.state == 5
        and row.local_addr == loopback
        and row.remote_addr == loopback
        and socket.ntohs(row.local_port & 65535) == remote[1]
        and socket.ntohs(row.remote_port & 65535) == local[1]
        and row.pid > 0
    ]
    if len(matches) != 1:
        raise ValueError("observer native TCP peer PID unavailable or ambiguous")
    pid = matches[0]
    return pid, process_user(pid), None


def foreground_client(gui, frame):
    user = gui.user
    user.GetClientRect.argtypes = [HANDLE, ctypes.POINTER(Rect)]
    user.GetClientRect.restype = ctypes.c_int
    user.ClientToScreen.argtypes = [HANDLE, ctypes.POINTER(Point)]
    user.ClientToScreen.restype = ctypes.c_int
    user.IsWindowVisible.argtypes = [HANDLE]
    user.IsWindowVisible.restype = ctypes.c_int
    user.IsIconic.argtypes = [HANDLE]
    user.IsIconic.restype = ctypes.c_int
    with gui.physical_coordinates():
        window = gui.foreground()
        bounds = gui.window_rect(window)
        if window != frame.foreground_window or bounds != frame.foreground_bounds:
            raise ValueError("foreground changed before state sample")
        pid, client, origin = DWORD(), Rect(), Point()
        if not (
            user.GetWindowThreadProcessId(window, ctypes.byref(pid))
            and pid.value
            and user.IsWindowVisible(window)
            and not user.IsIconic(window)
            and user.GetClientRect(window, ctypes.byref(client))
            and user.ClientToScreen(window, ctypes.byref(origin))
        ):
            raise ValueError("native foreground client unavailable")
        client_bounds = (
            origin.x,
            origin.y,
            origin.x + client.right - client.left,
            origin.y + client.bottom - client.top,
        )
        left, top, right, bottom = bounds
        if not (
            left <= client_bounds[0] < client_bounds[2] <= right
            and top <= client_bounds[1] < client_bounds[3] <= bottom
        ):
            raise ValueError("foreground client outside captured window")
        return window, bounds, pid.value, window, client_bounds

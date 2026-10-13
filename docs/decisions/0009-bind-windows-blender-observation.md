# Bind Windows Blender observations to native local identities

The optional public-RNA producer previously required a Linux Unix socket and
X-Resource PID lookup. Windows Python in the actual installation has no AF_UNIX
constant. Removing that platform check alone would neither work nor establish
the source of scene facts.

Reuse the fixed snapshot/nonce protocol and UI-thread collector. On Windows,
create a new private NTFS directory and port metadata file with an explicit
current-user owner and protected ACL. Bind IPv4 to 127.0.0.1 only. Resolve the
connected reverse TCP tuple through GetExtendedTcpTable, and verify the process
token user. The provider additionally requires the actual foreground window PID
to equal the server's native peer PID before accepting any snapshot. Caller
claims of a PID, user or host never establish identity.

Compare foreground handle, physical outer/client bounds and PID before and after
the sample. Retain the existing fresh nonce, acquisition interval, version and
unique RNA-window dimension checks. Standalone Blender loads helpers from the
same source directory without importing runtime ML dependencies. Linux retains
its existing transport and identity path.

This is a partial read-only observation route. It supplies public selection,
datablock identity, object properties, scene units, configured tools, raw keymap
inventory, editor layout and view pose. It cannot prove popup/input ownership,
effective keymap, text focus, IME or global idle. These stay UNKNOWN. An empty
modal list or an unlocked manager cannot authorize input. UI-thread timeouts
remain explicit unavailability, with no retry or relaxed freshness guard.

Native Windows transport tests and an owned factory Blender execution exercise
collector -> provider -> State Compiler -> all six operation guards. The guards
refuse input when required facts are missing; this does not establish successful
menu, transform or viewport workflows. Evidence and retained failed attempts are
recorded in docs/validation/2026-10-13/windows-blender-observation.json.

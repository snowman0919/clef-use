# Preserve the caller's Windows DPI context during capture

Status: accepted software correction, 2026-10-13.

An actual installed 0.1.37 capture changed an already-open owned Tk window from
2560x1600 physical pixels to1463x914. Its button moved from[88,385,823,595] to
[50,220,470,340]. MSS10.2.0's Windows constructor calls the process-wide
SetProcessDpiAwareness after the window exists. A temporary thread DPI context
cannot undo that process mutation. The frame itself retained2560x1600 pixels
while its foreground bounds changed. This also invalidated diagnostic GUI
readbacks that captured inside the GUI process.

Use native GDI for the Windows primary-monitor capture inside the existing
per-thread physical coordinate context. Keep the existing primary monitor at
origin(0,0), physical RGB frame, layered-window capture and foreground checks.
Create a top-down32-bit DIB, BitBlt with SRCCOPY|CAPTUREBLT, flush GDI before
reading, then decode BGRX to independent RGB pixels. Reuse the project's native
BitmapInfo definition and cached function-binding pattern. Destroy the wholly
owned memory DC before deleting its bitmap, then release the screen DC, including
on acquisition, copy and conversion failures. No process DPI setter is called.
Linux and macOS retain their existing capture implementations.

Alternatives: locking the caller's current process awareness still takes away
its ability to choose a later DPI policy. Restoring awareness after MSS is not a
supported reversal. Patching MSS private initialization or maintaining a fork
adds a second dependency contract. A separate capture process introduces an IPC
path and image copies. None is needed for this native Windows path.

The cost is maintaining the small GDI capture adapter alongside the existing
native Windows input/overlay/observer adapters. Capture still allocates and
retires its owned GDI surfaces per call; no cross-thread surface cache is added.
A future multi-monitor capture change must revise the primary-monitor contract,
not silently expand coordinates to the virtual desktop.

The native GUI regression fails before input with installed0.1.37, and passes
with the source correction, including real Unicode/selection/click/scroll
readbacks and exact owned cleanup. An alternating separate-process comparison
of100 captures per variant preserves identical RGB pixels and geometry.
Capture-only p95 is53.2624ms versus42.4806ms. This does not prove the whole
state-change-to-correct-input100ms gate, model accuracy, goodput or eligibility
coverage. Actual evidence is recorded in docs/EXECUTION_STATUS.md.

Primary contracts:
- https://learn.microsoft.com/en-us/windows/win32/gdi/the-virtual-screen
- https://learn.microsoft.com/en-us/windows/win32/gdi/multiple-monitor-system-metrics
- https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-createdibsection
- https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-deleteobject

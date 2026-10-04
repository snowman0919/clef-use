# Windows native input and validation

The Windows branch of `DesktopCapture` and `DesktopAction` uses the existing
semantic action contract with checked Win32 calls in `windows_input.py`.
macOS/Linux retain their existing input implementation. No additional native
extension, primitive MCP tool or production remote backend is introduced.

Reference: trycua/cua commit `542046496c4e8867b78bc0fde4f999a226af59cb`:

- [keyboard.rs](https://github.com/trycua/cua/blob/542046496c4e8867b78bc0fde4f999a226af59cb/libs/cua-driver/rust/crates/platform-windows/src/input/keyboard.rs):
  checked `SendInput`, UTF-16 Unicode input and confirmed foreground targeting.
- [mouse.rs](https://github.com/trycua/cua/blob/542046496c4e8867b78bc0fde4f999a226af59cb/libs/cua-driver/rust/crates/platform-windows/src/input/mouse.rs):
  pointer movement/readback and checked mouse injection.
- [capture_admission.rs](https://github.com/trycua/cua/blob/542046496c4e8867b78bc0fde4f999a226af59cb/libs/cua-driver/rust/crates/platform-windows/src/capture_admission.rs):
  screenshot/target identity and coordinate invariants.
- [interactive task packaging](https://github.com/trycua/cua/blob/542046496c4e8867b78bc0fde4f999a226af59cb/libs/cua-spacesd/packaging/windows/install-scheduled-task.ps1):
  distinction between service session 0 and the user's interactive desktop.

This is an independent Python/stdlib implementation of Windows APIs. No cua
source, scheduled-task installation, privilege elevation, foreground-assist or
background-input machinery is copied or installed.

## Invariants

Each screenshot records its foreground HWND and uses physical pixels under a
restored per-monitor DPI context. Input validates the current interactive/default
desktop and the captured foreground. A changed target is an error before any new
press, including a focus change during the corner-failsafe check. A permitted
click can focus another window; text in the same action still requires the
original captured foreground. A subsequent observation can establish the new
window before another action.

Session 0, an unavailable/secure desktop and absent foreground fail explicitly.
Doctor checks desktop availability without sending input and cannot mark session
0 ready. This check does not establish permission to inject into elevated apps;
UIPI can still block input. Every individual `SendInput` must report one inserted
event; this confirms admission, while visible readback confirms effect.

Windows text uses paired UTF-16 input events, including surrogate pairs, without
changing the clipboard. Text control characters remain refused. Cancellation and
focus changes stop later characters. Owned keys/buttons/Unicode units are released
on errors; failed releases remain tracked for retry. Cleanup bypasses the pointer
corner failsafe, then restores its setting. Pointer moves are bounded by the
virtual desktop and require exact position readback.

## Observed evidence, 2026-10-04

Windows 11 Pro x86_64/Python 3.12.10 on Pocket4, session 1/default desktop,
2560x1440 primary monitor. An on-demand, least-privilege InteractiveToken task
runs the task-owned validation process; the normal SSH process remains session 0.
No unlock, security-policy change, autostart task or external app edit is used.

`scripts/windows_gui_smoke.py` creates and closes a disposable native Tk window.
It checks actual widget readback for Korean/emoji text, Ctrl+A/Backspace, one click
and two clicks, wheel events, pre-input cancellation and refused control text;
it checks clipboard preservation, stale-foreground refusal and native held-input
state after release. Captures are real Windows pixels. Only this window's crop is
retained as public evidence. See `evidence/windows-native-gui.json`.

`scripts/windows_model_gui_agent.py` plus `windows_model_gui_smoke.py` is a
**diagnostic-only** SSH loopback bridge. The canonical SessionRuntime, pinned
OmniParser CPU and CLEF-Flash MPS run on macOS; canonical Windows capture/input
operate on the disposable real Windows window. There is no per-click outer model
intervention, manual candidate injection, synthesized screenshot or simulated
actuation. The application independently reports Continue/Confirm callbacks and
its visible completion text. This proves that vertical slice; it does not prove
Windows-local ML, a Windows GPU backend, arbitrary applications or unattended
locked-desktop operation. It is not a supported deployment/remote backend.

Initial run completed 2 native actions / 4 decisions in 99.334815s, with two fresh
completion observations and app readback `Task complete`. Model and input hosts
are explicit in `evidence/windows-model-gui-initial.json`; the final packaged
adapter rerun completed the same 2 actions/4 decisions in 213.569719s
(`evidence/windows-model-gui.json`). Both include cold worker loading, with
uncontrolled host load; this variation is not a measured speed improvement.
The screenshot is scoped to the test app.

Reproduce adapter validation from an interactive Windows process:

```powershell
python scripts/windows_gui_smoke.py --output windows-native-gui.json
```

Running that command in an SSH/service process is expected to refuse session 0.
Keep user apps untouched, use only the disposable test window, and restore prior
pointer/foreground/clipboard state. The diagnostic bridge binds loopback only,
uses an ephemeral token read from a private file, and requires a private SSH
forward when its controller runs on macOS. Never expose that test endpoint publicly.

## Visual iteration, 0.1.5

Captured physical foreground bounds now guard input against window movement.
Shortcut scan codes use the foreground thread's keyboard layout, and release
reuses the original key-down event even after layout changes. Clipboard sequence
is checked by the diagnostic without reading/writing clipboard. Installed-wheel
Windows tests and native GUI passed (evidence/windows-015.json and
windows-native-015.json). pythonw could not acquire foreground in this session;
the ordinary Python console task acquired the owned test window through normal
Windows focus calls. Failed admission retained the no-input guard.

The runtime's screenshot-only waiter, explicit modes and exact-image perception
cache are documented in VISUAL_READINESS.md. Two correct real model-selected
clicks and app completion readback were observed with 500ms delayed rendering,
but an MPS backend error interrupted final model verification in the initial
0.1.5 run. Do not interpret that ERROR as runtime completion.

A later cold run of the same 0.1.5 canonical runtime completed two correct native
clicks and four model decisions in 69.990643 seconds, with two fresh completion
observations and independent `Task complete` readback. Parser calls: 3; CLEF
calls: 4; exact perception cache hits: 1. See
`evidence/windows-visual-recovery.json`. Inference remained on macOS MPS/CPU;
input remained on the actual Windows desktop. This single successful run does
not resolve earlier intermittent MPS failures or establish a latency improvement.

## Windows-local ROCm diagnostic

The native Windows-local run in `evidence/windows-local-inference.json` passed
with Radeon 890M/gfx1150, Python 3.12.10, PyTorch 2.11.0+rocm7.14.1,
Transformers 5.10.2 and bitsandbytes 0.50.2. OmniParser ran in a separate CPU
environment with PyTorch 2.11.0+cpu / Transformers 4.46.3. The original pinned
models were copied and verified; the vision tower, output embeddings and typed
head remained FP16 while 248 language modules used NF4 double quantization.

The tested AMD wheel selection for that isolated Python 3.12 environment was:

```powershell
python -m pip install --index-url https://repo.amd.com/rocm/whl-multi-arch/ `
  "torch[device-gfx1150]==2.11.0+rocm7.14.1" `
  "torchvision[device-gfx1150]==0.26.0+rocm7.14.1"
```

This is a diagnostic environment, separate from the released `models prepare`
Python 3.11 lock. The remaining CLEF/Omni dependencies used the canonical hashed
locks with accelerator packages removed, then separate native Torch builds.
The report records actual installed versions and tested source hashes.
See [AMD installation](https://rocm.docs.amd.com/projects/ai-ecosystem/en/latest/frameworks/pytorch/install.html)
and [compatibility](https://rocm.docs.amd.com/en/docs-7.14.1/compatibility/compatibility-matrix.html).
The test did not change drivers or security settings; compliance of the installed
driver with the current official matrix was not established.

To reproduce the GUI slice with those prepared environments, use the existing
owned-window agent in an interactive Windows session, a private generated token
file, and an isolated `CLEF_USE_CONFIG` pointing to the models and interpreters.
The controller can run over SSH on the same Windows machine; its endpoint stays
on Windows loopback, so this mode does not need an SSH port forward.

```powershell
python scripts/windows_model_gui_smoke.py --token-file "$validationRoot/gui-token" `
  --port 37945 --rocm-worker scripts/windows_rocm_worker.py `
  --output "$validationRoot/windows-local-gui.json"
```

`$validationRoot` is the private directory passed to the agent's `--root`;
start the agent with the same port. The controller initializes both resident
workers before resetting and focusing that owned window once. The experimental
loader reuses the canonical worker protocol, request conversion, typed decision
backend and runtime. It checks actual quantized module types before admitting
inference and rejects CPU readiness. It is not the released default backend.
Keep the original refusal/result files; the controller refuses an existing
output. One native task completed two clicks/four decisions in 118.6999s after
preinitialization, with two fresh final observations. No arbitrary-app stability,
general quantization accuracy or latency improvement is inferred.

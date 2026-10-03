# Engineering handoff

Updated 2026-10-04. Repo clef-use/main, public origin
https://github.com/snowman0919/clef-use. Previous HEAD efde70d, now owned 0.1.4
Windows native-input change in progress. Overall goal remains active; numbered
requirements: IMPLEMENTATION.md; evidence: evidence/VALIDATION.md.

Canonical runtime owns capture -> pinned OmniParser -> semantic candidates ->
joint CLEF choice/noul/score -> deterministic input -> fresh verification. CLI
and five MCP tools share one resident core. No shell primitive/per-harness core.

Authorization: external SSD /Volumes/SSD/AI/clef-use, public repo/push, Windows
ssh win. Latest user explicitly authorized actual Windows GUI and asked to
reference trycua/cua. The old GUI deferral is superseded for Windows only; Mac
foreground/input remains deferred. Preserve user settings, apps, changes/secrets.
Production deployment route is still unanswered; public latest was HTTP 404.

0.1.4 Windows DesktopCapture/DesktopAction use stdlib ctypes Win32 input, checked
SendInput counts, physical DPI coordinates, captured foreground identity,
interactive/default desktop guard, clipboard-free UTF-16 text and tracked cleanup.
Session 0/secure desktop/changed focus are refused. Doctor probes desktop without
input. cua source pin, independent design and reproduction: WINDOWS_INPUT.md.

Owned frozen source passed 57 tests, lint/format and wheel build. Task-owned
Windows Python3.12 installed non-editable 0.1.4 wheel and passed 57 tests/4.57s;
actual native Tk GUI passed Unicode/emoji, clipboard, shortcut, click/double-click,
wheel, cancellation/control refusal, changed focus and no-held-input readbacks.
Real Windows GUI + Mac Omni CPU/CLEF MPS diagnostic loop completed 2 native
clicks/4 decisions, no outer interventions, 99.334815s; actual app readback
Continue -> Confirm -> Task complete. Final installed-wheel rerun also completed 2 actions/4 decisions in
213.569719s; both cold loads vary with uncontrolled host load. No Windows-local ML/GPU, arbitrary app/calculator or Mac-input proof.
Windows tests use an on-demand least-privilege InteractiveToken task, no security
policy changes/elevation/autostart. Close only disposable own windows; cleanup
SSH forward, own finished task and ephemeral tokens before ending the test.
These resources were removed after final GUI completion.

Windows workspace: %LOCALAPPDATA%/clef-use-validation-20261004. source/.venv holds
our 0.1.4 installed wheel; clean Git source remains previous 000885b until own
push/pull. windows-native-src is a temporary frozen-source diagnostic copy; final
native reruns import installed wheel. Mac pure tree /tmp/clef-use-windows-audit,
clean tool env /tmp/clef-use-audit-env. Original project .venv remains unmodified.

Earlier 0.1.3 CI 37143721190, release 37143721968 and doc CI 37144979945 passed;
0.1.3 site had all 15 platforms/Python targets and retained 60 hashes. Installed
Mac exact assembled 0.1.3 and config byte-preserved. 0.1.4 artifacts/CI to be
recorded after source push; do not replace existing version hashes. Existing
transfer dist/clef-use-release-site-0.1.3.tar.gz is now historical; latest delivery
must include the 0.1.4 release and latest metadata, preserving older versions.

Unowned edits are preserved and excluded from source/CI/release:
README.md; docs/INSTALL.md; docs/{ja,ko,zh-CN}/README.md; backends.py worker/CLEF
sections; cli/client/config/model_worker/models/provision; doctor acceleration
sections; service model holds/unload; tests/test_protocol.py extra model-hold;
acceleration.py, mlx_support.py, quantization.py, quantization_prepare.py;
extra acceleration/model-residency tests and MLX/quantization/residency evidence.
Stage only owned backends/doctor blobs from the frozen HEAD+owned tree. Do not run
dirty-source tests or publish unrelated edits. No subagents were delegated.

Next bounded actions: checkpoint reviewed Windows patches; validate CI/native
release+installation. Then implement the newly received user-requested visual
condition waiting, action-effect/stale ROI checks, explicit non-action decisions,
structured effect history and exact-image perception cache. Preserve strong
completion checks and bounded cancellation; measure effects before speed claims.
Refresh public metadata when an authorized route is available. Public install cannot be claimed until latest metadata/artifacts
and isolated public one-line installs work. Keep Windows-local ML and broader GUI
coverage explicitly separate. Full Hermes launcher still missing; Codex readback,
OMP native MCP and official Hermes discovery/handler passed at earlier checkpoint.

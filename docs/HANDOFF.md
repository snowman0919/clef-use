# Engineering handoff

Updated 2026-10-04. Repository: clef-use, main. Public origin:
https://github.com/snowman0919/clef-use. Implementation base 7c734f1 (0.1.1).
Final task-owned documentation/evidence records public-host readback and this handoff.
Objective/invariants: IMPLEMENTATION.md. Observed gates: evidence/VALIDATION.md.

CLI and five high-level MCP tools share one authenticated resident runtime.
Actual CLEF MPS + OmniParser CPU models/cache are on the authorized external SSD
/Volumes/SSD/AI/clef-use; preserve unrelated files and all harness configuration.
The operator deferred GUI testing: no foreground change or input on Mac/Windows.
They authorized `ssh win` installation/protocol tests and reported deployment.

35 tests/lint/format pass locally. b352ab9 CI passed six jobs. Complete 0.1.0
release run 37136579094 passed all 15 native platform/Python jobs plus assembly;
downloaded to /tmp/clef-use-release-010-complete, all archive hashes verified.
Initial Intel build failed missing maturin; pinned backend fixed the actual jobs.
0.1.1 run 37137294737 passed all 15 targets and assembly. Both complete trees
are hash-verified in release-site, latest 0.1.1, with immutable 0.1.0 retained.
Installed user launcher updated canonically to exact assembled 0.1.1; repeat
returned CURRENT, fixture self-test passed, config bytes unchanged. Transfer
bundle: dist/clef-use-release-site-0.1.1.tar.gz plus adjacent SHA-256.

Real model run COMPLETED in 88.643 seconds. Two repeated resident-worker samples
also completed (81.661/33.037 seconds), two actions/four decisions each. All use
generated pixels and simulated actuation, no native GUI proof. Earlier MPS errors
remain documented; arbitrary model stability and CUDA are unverified.

Operator Windows 11 Pro / PowerShell 5.1 / Python 3.12.10 SSH passed all 35 tests,
packaged first install, CURRENT, CMD update and three rollback cases. Doctor
initialized five MCP tools, correctly ready=false with missing ML/disabled capture.
Private task directory: %LOCALAPPDATA%/clef-use-validation-20261004. Repeat on 0.1.1
also passed; latest report is evidence/windows-ssh.json. Keep input disabled. uv normal stderr caused initial
PS5 orchestration failure, resolved with Python subprocess logging.

Codex config readback and actual OMP client passed. Hermes config installed but
existing launcher has missing runtime. No unrelated configurations changed.
Public install.sh/install.ps1 HTTP 200; latest manifest and SHA256SUMS HTTP 404.
Earlier 403 was Cloudflare default Python UA; project UA fix committed. Public
served bootstraps predate that fix. Async deployment-route question pending; need
existing SSH/SFTP alias/path or exact upload command, never credentials in chat.

Installed 0.1.1 doctor confirmed five MCP tools, dependencies, pinned cache and MPS;
ready=false is correct with capture disabled.

Next: if deployment
access is supplied, use the explicit configured route, upload version first/latest
last and verify public HTTPS install on isolated Mac/Windows. Otherwise provide
the exact transfer bundle and keep public acceptance open. GUI remains deferred;
do not mark the goal complete. The goal is active without a token budget.

Concurrent unowned changes appeared in acceleration.py, quantization.py,
quantization_prepare.py, config.py, cli.py, doctor.py, model_worker.py and
provision.py. Do not overwrite or include them in this task commits. User
clarification is pending. Current release acceptance is pinned to 7c734f1,
not these unvalidated working-tree edits.

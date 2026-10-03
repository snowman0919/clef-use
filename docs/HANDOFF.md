# Engineering handoff

Updated 2026-10-04. Canonical repository: `clef-use`, branch `main`, initial
implementation not yet committed. Objective and acceptance gates are in
`IMPLEMENTATION.md`; the active Codex goal retains the full attached request.

CLI and MCP share one authenticated local service and bounded session core.
31 meaningful runtime, protocol, configuration and installer unit tests passed
before the most recent safety changes; those changes need another test run.
CLEF-Flash performed real semantic inference on MPS with correct invoice answers.
OmniParser initialized, but Florence generation failed with a text-only attention
mask after image embedding expansion, on Transformers 4.49 and 4.46.3.
The next action is a minimal adapter matching Microsoft's documented generation
arguments, followed by real perception and joint decision tests on synthetic
pixels. Fixture tests do not establish real desktop behavior.

All ML weights, environments, OCR assets and source are on the user-authorized
external SSD under `/Volumes/SSD/AI/clef-use`. Existing SSD data and harness
configuration must be preserved. The user deferred GUI testing: no foreground
changes or desktop input until a later explicit test window. Real GUI acceptance
is therefore NOT_RUN. No secrets or model weights belong in the public repo.

Remaining gates: input-release and worker lifecycle regressions; lint; actual
offline first install/update/corrupt-download rollback; production packaging and
CI; multilingual/community documentation; persistent harness setup/readback;
authorized public GitHub creation/push; FTP hosting verification. Hermes's
existing launcher references a missing environment, so runtime integration there
cannot yet be claimed. FTP publication credentials are not established.

Private diagnostic evidence currently includes `/tmp/clef-use-tests-second.log`,
`/tmp/clef-use-omni-compat-debug.log`, `/tmp/clef-use-wheelhouse.log` and
`/tmp/clef-use-doctor.json`. Transfer meaningful final results into repository
evidence documentation, excluding actual screenshots and personal content.

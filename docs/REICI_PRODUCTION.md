# Reici production acceptance and evidence

## Goal and authority

The user-designated `/home/monad/develop/prompt.md` (1,090 lines, read in full)
defines this task: improve and commit clef-use while producing a recognizable,
rigged, expressive VRM 1.0 avatar through meaningful clef-mcp and blender-mcp
participation. Technical milestones alone are not completion.

Starting state: canonical main at c86d499, clean; installed runtime 0.1.21.
Preserve unrelated work, original reference images and the existing Blender
process. Local coherent commits are authorized. Remote publishing is not.

## Acceptance checks

- Actual CLEF + OmniParser execution of Blender UI goals; exact MCP call/results
  and per-stage latency logs retained. Reproduce/fix/retry general failures.
- Visually inspect body, face, hair, outfit, accessories and materials separately.
- Humanoid and finger rig: actual evaluated deformation under representative poses.
- Expressions: neutral, blink/bilateral blink, happy, angry, sad, surprised, A/I/U/E/O;
  visible tests, nonempty morph deltas and export bindings.
- Physics: hair/ribbon/loose details with collider-aware motion inspected, not just
  spring entries present.
- Actual VRM 1.0 export and import; inspect final character and retain source blend,
  renders, support assets and asset inventory.
- Clean local release tree and isolated HTTP installation/update exercise; checksum,
  interruption safety, idempotency, CLI/version/doctor/MCP startup verified.
- Regression tests and consistent en/ko/zh-CN/ja setup documentation.
- Final E2E rehearsal using corrected runtime and coherent Git commits.

## Sources and output ownership

Task-owned assets and large binary outputs: `/home/monad/develop/reici-production`.
Original reference cache files are copied, never edited. Two reference images
were recovered; the third reference mentioned in the prompt has not been found.
Unseen views must be identified as derived, not falsely called canonical.

The existing Blender process and user preferences are not modified. A dedicated
GUI session on an isolated virtual X11 display is used for reproducible dogfood
without injecting input into other user applications. This is an actual Blender
GUI, not a headless Blender-only replacement; physical-desktop generalization
must not be inferred from it.

## Initial defect: first-call diagnostics

OBSERVED: native clef-mcp `computer_status()` and `computer_observe()` failed with
`runtime refused ...; inspect session status`. Service health was healthy, idle;
HTTP status returned 400/KeyError. SessionManager indexed an empty session map.
The client discarded the response and told a failing status caller to query
status again.

Correction: distinguish NO_ACTIVE_SESSION and SESSION_NOT_FOUND without creating
fake sessions or initializing models. Preserve public SessionResult semantics.
Only recognized, bounded error codes are translated to static actionable text;
untrusted HTTP response text is not echoed. Regression checks cover status,
observe, abort and explicit unknown IDs through the actual authenticated HTTP
client/server path. All four failed before the correction.

## Completion status

IN_PROGRESS. No character, physics, final E2E or installer completion claim is
made by this document. Evidence and incomplete acceptance criteria will be added
as the actual production workflow is exercised.

# Changelog

## Unreleased

- Extend the optional read-only Blender state provider to Windows using private
  NTFS endpoint metadata, IPv4 loopback native peer PID/user verification and
  physical foreground client bounds. Preserve UNKNOWN input-owner, popup, IME,
  effective keymap and idle facts; unavailable state cannot authorize operations.
- Keep the Windows validation window's UI loop alive during once-only native
  input. Require full selection, exact text and click/wheel readback instead of
  assuming widget consumption after a fixed sleep; retain acknowledgement and
  verification timestamps separately from reaction-performance claims.
- Retain private Codex stderr beside its verification trace and preserve native
  shortcut selection/text readback before assertions, including failing runs.
- Match native Windows shell-escaped guide paths during Codex verification and
  retain negative-trigger checks across Windows separators. Advertise accurate
  read-only MCP tool effects without changing the harness's approval policy.
- Refresh previously managed integrations against the newly installed executable,
  instead of probing a retained previous release against the new guide contract.
- Correct temporary Codex verification overrides so existing MCP server names,
  including dots, quotes and Unicode, keep their transport configuration while
  other configured servers are disabled for the read-only session.
- Restore Windows smoke-test pointer/focus before closing the owned Tk window,
  synchronize cross-thread foreground activation once, and retain cleanup errors
  in the result instead of losing the original verification evidence.
- Preserve Blender's public owning-manager interface lock as positive busy
  evidence. Compile only true to `loading=true`; unlocked or unavailable remains
  UNKNOWN and cannot authorize input. Retain native identity/freshness guards.
- Distinguish attempted harness tool calls from successful MCP responses. Error
  results cannot pass invocation; negative triggers reject failed attempts too.
- Retain validated integration bytes and guide inventories through capability
  discovery; refuse concurrent edits before journaling instead of overwriting them.
- Apply explicit text-focus and IME shortcut guards to modifier gestures before
  pointer movement, independently of optional post-input transition checks.
- Preserve exact normalized geometry and conflicting action/confidence/source
  evidence when identifying parser objects; deduplicate only equivalent records.
- Apply an explicit visual primitive before budgeting structured candidates so
  irrelevant literal alternatives cannot evict requested clicks or scrolls.
- Preserve extended scan-code and modifier-side distinctions when checking
  unowned Windows input. Refuse unknown held-key mappings instead of treating
  zero scan codes as shared ownership.
- Retire successful Windows guardian key/Unicode release acknowledgements so
  later parent EOF cannot replay them against a new owner's hold. Preserve only
  failed releases for the existing EOF recovery attempt.
- Normalize the API-assisted Blender fixture's numeric readback and preview to
  supported declared distance/angular units. Preserve raw exact-property values
  and dimensionless scale; unsupported distance requests remain refused.
- Anchor complete scene length conversion for numeric translation and its owned
  modal cancellation, including native input and final readback. Refuse missing
  settings or same-label scale/scene drift; leave rotation/scale independent of
  scene length settings. Advertise conditional requirements in registry v6.
- Collect scoped Blender `active_tool` evidence from initialized workspace tools
  and independently bound native context mode. Preserve area identities and
  UNKNOWN focus/dispatch; reject ambiguous, malformed or overflowing evidence
  without creating tools or weakening operation guards.
- Validate legacy X11 keyboard bindings before input, including implicit Shift.
  Refuse stale mappings without sending a wrong key, retain physical codes for
  release and preserve keys already held outside the legacy action.
- Anchor viewport view readback until native gesture button acknowledgement so
  an independent pre-input change cannot verify a no-effect gesture. Preserve
  expected drag changes and all other context guards after acknowledgement.
- Interpret location property values as raw Blender coordinates using validated,
  anchored scene units and explicit meter input. Keep scale dimensionless; refuse
  unknown units and numeric conversion range loss before input. Advertise conditional
  field requirements and value semantics in operation registry v5.
- Recheck cancellation/deadline after context sampling and before each native
  Windows Unicode unit. Reject invalid UTF-16 payloads before inserting a prefix.
- Restore supported X11 clipboard contents on confirmed pre-paste cancellation
  with an explicit bounded native acknowledgement. Release owned modifiers first,
  preserve concurrent copies and retain offered text once paste delivery is possible.
- Require complete stable selection identities across changing operations,
  readback and owned cancellation, including native input boundaries. The Blender
  observer uses process-scoped public session UIDs and exposes all six location/
  scale scalar properties. Missing identity remains unknown; same-name object
  replacement blocks input. Advertise the stronger contract as operation registry v4.
- Derive Blender view-effect revisions from the effective view matrix and
  perspective mode, keeping layout/region IDs and projection changes separate.
  Missing, incomplete or ambiguous view readback remains unknown.
- Preserve capture time through State Compiler processing so delayed screenshots
  cannot renew target geometry or foreground facts. Independently current provider
  evidence retains its own timestamp and validity.
- Resolve logical X11 buttons and wheel directions through the current OS pointer
  mapping. Release the acknowledged physical button during normal completion,
  independent abort and guardian recovery after executor exit.
- Require complete transform vectors before numeric input, recheck context and
  baseline before entry, and recheck the verified preview before commit. Verify
  all observed properties after a scalar edit, including unchanged fields/objects.
  Preserve the requested float in numeric text instead of rounding to 15 digits.
- Expose bounded raw Blender keymap inventory and native-client-bound editor
  layouts. Preserve duplicate/inactive bindings, tri-state modifiers and content
  digests; keep effective dispatch and editor focus unknown. Clipped or hidden
  regions never acquire a normalized rectangle by clamping their geometry.
- Map Linux capture coordinates using the captured monitor's pixel extent,
  avoiding displaced input when the X11 root spans multiple monitors. Keep
  macOS logical/Retina scaling unchanged.
- Recheck observed keymap content at operation dispatch and the native input
  boundary, even when the version label is unchanged. Revalidate viewport editor
  geometry before and during gestures, stopping and releasing owned input on change.
- Preserve every matching observed input as a distinct literal-text alternative.
  Reserve candidate slots for actual matches and request replanning before model
  or input execution when text alternatives exceed the existing action budget.
- Add an opt-in, read-only Blender public-RNA observer on Linux X11, bound to
  the native foreground client using Unix peer credentials and X-Resource PID.
  Keep unresolved popup, text/IME, effective keymap and busy state unknown;
  partial snapshots do not enable guarded operations. Expose independently
  sampled state and expire facts delayed by perception processing.
- Preserve each decision candidate's operation and observed target identity so
  equally labelled controls remain distinguishable by their actual geometry.
  Keep every executable target within the existing 40-object context budget;
  refuse overflow or missing targets instead of silently dropping their evidence.
- Keep Hermes MCP registration inside existing YAML flow mappings, respecting
  trailing commas and document endings while preserving user settings and comments.
- Ignore active-source aliases of the same complete managed skill directory
  during repeat enrollment; separate resource roots still report conflicts,
  including aliases of only SKILL.md with different relative references.
- Detect duplicate declared skill names in selected and other active skill
  sources, including nested directories with different folder names; preserve
  conflicting guides and configuration.
- Include Hermes trusted current-project sources and configured create/external
  directories in enrollment collision checks, preserving inactive project discovery.
- Match Hermes terminal working-directory validation: trim whitespace, expand
  the home directory, and ignore missing directories when no project is explicit.
- Recognize Hermes directory aliases, malformed-frontmatter name recovery and
  legacy Markdown guides without treating package support files as active guides.
- Ignore disabled Codex SKILL.md copies in collision reports and retain active
  guides when a configuration entry targets only their directory.
- Require prospective policy/eligibility evidence in reaction scorers; unknown
  coverage remains unmeasured and cannot pass release gates. Eligibility counts
  include verified opportunities independently of attempts and deadlines.
- Retain decision request UTF-8 budget bytes, object/question counts and bounded
  SDK-reported input tokens in numeric diagnostics without changing model packets
  or confidence gates. Missing and invalid token usage remain explicit.
- Order packaged guide manifest entries by relative POSIX spelling so Windows
  and Linux generate identical contract bytes from the same guide files.
- Bind local runtime requests to executable version, protocol and API fingerprint.
  Reject stale control and shutdown requests, prevent client-driven downgrades,
  and preserve active sessions and owned-modal recovery during idle upgrades.
  Explain retained matching-executable cancellation and explicit contract reload.
- Bundle three portable Agent Skills with actual schema/capability discovery,
  managed harness enrollment, release contract hashes, conflict preservation,
  and distinct discovery/load/invoke verification stages.
- Resolve OMP configuration names relative to HOME and preserve explicit default
  profile precedence. Reject absolute config names before writing to a location
  the native harness would not discover.
- Add typed keyboard, literal text, three-button pointer and modifier gestures
  with bounded ownership and independent native abort recovery.
- Validate finite UI transitions only after an acknowledged trigger; retain
  exact modal, loading, unit and coordinate-frame guards before input. Preserve
  owned-modal cleanup after abort and prevent replacement during pending recovery.
- Add provenance-aware State Compiler and six guarded Blender operation families.
  Missing hidden application state blocks execution. Native API-assisted fixtures
  verify effects; they do not establish pixels-only production support.
- Expose a bounded disposable Blender fixture through the real installed MCP
  service for native harness task checks, with independent RNA readback and
  deadline/signal/input/process cleanup evidence.
- Record pre-pruning candidate coverage diagnostics without relaxing confidence
  gates; distinguish singleton/uniform distributions and numeric false completions.
- Use unused executable-target slots for observed decision evidence within the
  existing 40-object packet limit, retaining deeper dropdown rows in ASSESS.
- Declare shared unknown defaults and model-only outward pixel envelopes to
  reduce repeated decision text while preserving exact native execution geometry.
- Clarify linked-reference loading and read-only Blender skill discovery after
  actual native Hermes guide-selection and reference-call failures.
- Keep deadline goodput separate from fast-path eligibility coverage; unrecorded
  eligibility remains unmeasured in native benchmark reports.
- Read localized guide contracts as UTF-8 and generate LF bytes independently of
  the build host locale, including Windows packaging.
- Use managed MCP/guide integration in all four localized quick starts and
  validate published CLI examples and inline tool arguments against the current
  parser and schemas during packaging.
- Preserve exact UTF-8 and newline bytes in atomic managed writes on Windows,
  keeping guide hashes and existing CRLF configuration compatible with recovery.
- Reuse a process-bound X11 query connection while reading fresh native guards;
  refuse changed logical key bindings and recover acknowledged physical keycodes.
- Replace X11 clipboard time-based restoration with verified application transfer
  acknowledgement. Preserve queued text after interrupted paste and concurrent
  clipboard ownership; require explicit clipboard delivery for Linux literals,
  including ASCII, because an idle IME can compose native key events.
- Observe actual editor change events in the native benchmark preflight instead
  of waiting a fixed interval before reading the widget.
- Keep CLEF-Flash/NF4 as default. No 100ms grade, cross-platform native acceptance,
  full harness task success or public release is claimed for this candidate.

## 0.1.29

- Accept genuine singleton action choices in archived/native decision benchmarks,
  including no-input ASSESS `none`, while preserving opaque identifiers and the
  empty/nonmapping/100-option boundary. Unlabelled evidence remains unlabelled.
- Enforce the whole encoded 8192-token limit before d1 backbone execution, not
  merely branch packing. Guard plain IDs, tree state plus packed branches and
  oversized branch sets before partial execution; restore scoped hooks/methods
  on success, refusal and setup/model failures under the pinned serial SDK contract.
- Preserve prompts, pixels, weights, precision, confidence gates and default
  CLEF-Flash/NF4. Normal saved-native d1 replay is compatible; no recognition,
  calibration, live completion, default promotion or avatar acceptance claim.
- Ship software only: no private screenshots/corpora, weights or third-party assets.

## 0.1.28

- Focus bounded decision evidence around a unique literal observed label in
  success conditions when a natural-language goal has no exact UI anchor and
  no explicit visual intent. Preserve raw objects and unchanged executable
  choices, context bounds, native-raster proximity and confidence/safety gates.
- Refuse ambiguous, substring-only, hidden, occluded, sensitive and blank
  fallback anchors; preserve existing explicit/exact-goal anchor priority.
- Retain CLEF-Flash/NF4 and opt-in d1. Saved-frame GPU diagnostics establish a
  context effect, not calibrated accuracy, fresh Blender completion or avatar
  acceptance; no captured data, model weights or third-party assets ship.

## 0.1.27

- Add explicit cache-only observation with MCP `refresh=false` and CLI
  `observe --cached`, preserving recorded frame/object/image and refusal evidence
  without capture, parsing, runtime initialization or service startup/restart.
- Fail closed on legacy services without a cached-observe capability, and bind
  capability/read requests to one authenticated endpoint against endpoint swaps.
- Reject non-boolean refresh policies at the client before startup and at the
  service before initialization. Preserve concurrent fresh-operation ownership.
- Retain default fresh observation, all confidence/completion/input safety gates,
  CLEF-Flash/NF4 defaults and opt-in d1. This release adds diagnostic UX, not proof
  of improved recognition, fresh completion or Reici visual acceptance.

## 0.1.26

- Explain confidence refusals with bounded mode/selection/goal/condition scores;
  keep the legacy selector score and all existing confidence thresholds unchanged.
  Clear transient blockers atomically before resumed workers start, preserving
  previous terminal payloads and unverified-completion evidence.
- Assess visible goals before requiring dense input targets, support no-input
  ASSESS runs, and require full completion evidence after measured visual effects.
  Preserve the two-fresh-positive completion rule; a changed ROI is not completion.
- Bound explicit semantic target choices and rank nearby context hints in native
  raster units instead of unit-square distance. Keep original labels/provenance
  and unchanged action/context limits; do not manufacture missing popup evidence.
- Scope NF4 placement to the backbone subtree, release obsolete owners of the
  never-executed output table, and isolate ML readiness from ambient Python paths.
- Keep private one-shot numeric head-boundary capture opt-in and disabled by
  default, with descriptor-relative path, bounded-write and cleanup guards.
  No captured data, model weights or third-party avatar assets ship in releases.
- Separate independent source-suitability reviews from production acceptance and
  require actual image-open/model/hash evidence for Gemini review transport.
- Retain CLEF-Flash/NF4 defaults and the opt-in d1 candidate. This release does not
  claim improved Blender recognition, calibrated model accuracy or Reici completion.

## 0.1.24

- Freeze the pre-V2 implementation under `old/` and port reviewed components into a clean
  V2 tree (structured routing always bounded; effect-evidence completion gate calibrated
  against the real checkpoint; dense-screen decision overflow crash fixed; observation-bound
  canvas actions, SigLIP2 grounding path).
- Gemini-AGY strict CV reviewer adapter for asset ranking and production gates.

- Deliver the previous action's verified visible effect (bounded ROI crop plus facts)
  into the next CLEF decision, so a genuinely changed viewport region no longer
  collapses into NEEDS_REPLAN "lacks required visible condition evidence"
  (Blender dogfood finding F1; regression: tests/test_effect_evidence.py).
- Add configurable structured/visual/canvas routing before candidate truncation,
  bounded CLEF decision context, and confidence/entropy-triggered visual fallback.
- Add isolated frozen SigLIP2 coarse-to-fine grounding and optional supervised
  dense target-score/offset heads with positive/negative independent-split provenance.
- Support explicit whole-region coarse overviews with native fine crops and V3
  checkpoint validation of trained strategies; retain distinct letterbox-edge patches.
- Compare supervised target components through conditional spatial confidence
  with a configurable binary-score floor, retaining ambiguity and absent-target checks.
- Extend observation-bound native gestures with drag, move, double-click and
  scoped scrolling while retaining fresh-frame, progress and abort checks.
- Preserve unverified completion assessments for planner escalation instead of
  issuing another visual input that can undo the visible result.
- Reground model-generated pointers after same-window tooltip/redraw changes
  within the existing retry budget, preserving strict input references and window guards.
- Capture native X11 foreground identity and geometry; require established window
  metadata for redraw retries and preserve the original Windows double-click target.
- Add real isolated Blender stress benchmarks with independent state readback,
  retained failures, execution-mode success rates, separate raw/choice counts,
  round wall latency and persisted runtime outcomes before native readback.
- Use CPU SDPA for CLEF, retain replayable trial-attributed model requests, and
  balance coarse/fine supervision with seeded epoch shuffling and separate
  stage validation metrics.

## 0.1.22

- Add planner-supplied, observation-bound canvas clicks and continuous left-button strokes through the existing high-level MCP/runtime/CLEF loop.
- Restrict pointer runs to supplied paths; reject stale frames, sensitive surfaces, out-of-window points and contradictory input payloads while preserving cancellation cleanup and confidence/completion gates.

- Distinguish absent/expired GUI sessions from runtime failure and provide actionable first-call MCP diagnostics without starting model inference.
- Track the reference-character Blender/VRM production acceptance criteria and real dogfood evidence.
- Preserve the live installation when interruption arrives immediately after the atomic activation switch; keep previous runtime receipts and user data unchanged.
- Align localized installation commands and document repair, removal, and forced-termination limits.
- Move CUDA NF4 output-embedding offload ahead of joint-head allocation when GPU memory is low; avoid installing hooks on an already-CPU embedding.
- Cache only byte-identical icon crops with pinned float32/NumPy crop semantics and allow idle observations to outlast the short control-call timeout.
- Reobserve delayed completion transitions without repeating input, preserve inference-log counts at budget exhaustion, and record candidate-building latency.

## 0.1.20

- Explain installation stages and offer model preparation with a Y/n prompt.
- Report preparation stages and periodic progress while long operations run.
- Validate repeat installations across Python minors using verified release receipts.
- Continue Windows Python discovery past unusable launcher candidates and handle Unicode pip diagnostics.
- Reduce CUDA NF4 resident memory by moving unused output embedding rows to CPU when free VRAM is low; initialization must still fit.
- Publish verified artifacts for 15 installer targets through the dedicated dev runner.
- Record public Windows and monad installation, preparation, MCP/GUI execution, update and removal, including recovery and cache-reuse limits.

## 0.1.3 - Release candidate

- Refresh idle MCP observations with matching objects and pixels; reserve the desktop during parsing.
- Record budget/refusal terminal reasons and failed backend elapsed time without phantom benchmark samples.
- Support Unicode and spaces in per-user Windows installation paths; exercise those paths in native installer checks.

## 0.1.2 - Release candidate

- Track ordinary key presses and ASCII typing before native key-down calls.
- Release implicit Shift and Windows keyboard-layout modifiers after failures.
- Attempt every owned key/button release, retaining failed releases for retry.
- Cover cancellation during a held-key sequence without native GUI input.

## 0.1.1 - Prior candidate

- Correct semantic action history and final-state completion context.
- Make empty OCR and pinned Florence captions follow the upstream parser contract.
- Identify the HTTPS release client explicitly and isolate Windows test PATH changes.
- Include the pinned build backend needed for macOS Intel dependency wheels.
- Keep 0.1.0 installation checkpoints immutable; update them through the same verified installer.

## 0.1.0 - Initial implementation

- Shared resident runtime behind five high-level MCP tools and a thin CLI.
- Pinned CLEF/CLEF-Flash and OmniParser visual object/action selection.
- Bounded sessions, cancellation, input cleanup and visual progress checks.
- Atomic verified offline wheel installation and the same update implementation.
- POSIX and PowerShell bootstraps; multilingual initial setup documentation.
- Protocol, configuration, state-machine and installer validation.

Real desktop acceptance and production hosting are tracked in
[validation evidence](docs/evidence/VALIDATION.md). No performance advantage or
untested platform support is claimed.

# Changelog

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

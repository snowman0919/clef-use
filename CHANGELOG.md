# Changelog

## 0.1.1 - Release candidate

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

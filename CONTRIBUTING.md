# Contributing

Start with an issue describing a reproducible failure or a measured opportunity.
Keep runtime behavior in the shared core. Harness changes belong in configuration
adapters. Preserve unrelated user settings and never commit model weights,
screenshots, credentials or private session logs.

Use Python 3.11 for ML preparation and Python 3.11-3.13 for the runtime:

```sh
uv sync --locked --no-editable
PYTHONPATH=src uv run --no-sync pytest -q
uv run --no-sync ruff check src tests scripts
uv run --no-sync ruff format --check src tests scripts
uv run --no-sync python scripts/build_installer.py
git diff --exit-code install.sh install.ps1
```

Protect a concrete invariant with tests. Explain what real execution establishes
and what remains NOT_RUN. Real desktop tests require an operator-controlled
window. Synthetic pixels and fixtures do not prove desktop success or speedups.
English documents are canonical; preserve identifiers and examples in translations.

Use focused pull requests with a problem, resulting behavior and validation.
Do not report security vulnerabilities publicly; see SECURITY.md.

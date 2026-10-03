# Development

```sh
uv sync --locked --no-editable
PYTHONPATH=src uv run --no-sync pytest -q
uv run --no-sync ruff check src tests scripts
uv run --no-sync ruff format --check src tests scripts
uv run --no-sync python scripts/build_installer.py
uv run --no-sync python scripts/build_release.py
```

Use a non-editable install when the filesystem marks `.pth` files hidden; Python
can ignore hidden `.pth` files. `PYTHONPATH=src` explicitly tests current sources.
Release smoke checks strip PYTHONPATH/PYTHONHOME to verify the installed wheels.

`uv.lock` pins runtime/dev versions. Export runtime hashes with
`uv export --no-dev --no-emit-project --format requirements-txt`.
`requirements/ml-*.in` and bundled hashed `assets/ml-*.txt` pin isolated ML
environments. Re-resolve only after compatibility tests. Florence uses
Transformers 4.46.3; CLEF uses 5.10.2. Model and source revisions are explicit.

Ordinary tests require no physical desktop or paid API. They verify typed
contracts, geometry, gates, stale/changed states, input cleanup, service security,
real stdio MCP and shared CLI behavior. Real model smoke uses generated pixels:

```sh
PYTHONPATH=src uv run --no-sync python scripts/model_smoke.py --output model-smoke.json
```

Run actual GUI tests only in an operator-provided window. Preserve private logs
locally. Do not commit real screenshots, user configs, secrets or cache files.

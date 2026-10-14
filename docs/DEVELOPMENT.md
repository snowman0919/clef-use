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

For native harness task verification, `scripts/blender_operations_fixture.py`
can expose the selected installed package's real authenticated loopback service
on a disposable factory Blender/Xvfb desktop. Invoke the script with that
installation's `runtime/current/bin/python`, `--runtime`, a newly owned
`--output`, unused `--display`/`--port`, and `--serve-seconds 1..600`. The ready
descriptor declares its `API_ASSISTED_FIXTURE_ONLY` provider and one bounded
numeric-transform task. Keep the endpoint token private. Use the descriptor's
`CLEF_USE_STATE_DIR`, `DISPLAY` and Xauthority for the actual MCP process; verify
the installed schemas and full guide loads before allowing input. Check fresh
external RNA and pixels after the call, then request `shutdown_idle`.

Deadline or signal cleanup releases owned input, cancels only an observed modal
owned by this fixture, closes its service and removes its endpoint. Reports also
require owned Blender/Xvfb exit. A typed operation `SUCCEEDED` with session
`NEEDS_REPLAN` verifies the effect only; the fixture has no whole-goal perception
or decision backend and does not establish a production provider or latency gate.

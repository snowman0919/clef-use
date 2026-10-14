# Quick start

Put Calculator in the foreground in a controlled desktop. Do not use unrelated applications during execution. Ctrl-C or abort from another shell cancels the session. The runtime executes multiple actions without per-click planner calls.

Choose the harness you use: replace `codex` below with `hermes` or `omp`. The managed integration installs MCP and the selected guides together. Restart the harness, then inspect each verification stage; `NOT_RUN` is not task success.

```sh
clef-use doctor
clef-use models prepare --python python3.11
clef-use integrate codex --dry-run
clef-use integrate codex --scope user
clef-use integrations verify codex --live --read-only
clef-use run 'In the open Calculator, compute 123 * 456' --success 'Calculator shows 56088'
clef-use status
clef-use abort
clef-use update
```

[Installation](INSTALL.md) | [MCP](MCP.md) | [Harness](HARNESS_SETUP.md)

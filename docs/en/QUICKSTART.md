# Quick start

Put Calculator in the foreground in a controlled desktop. Do not use unrelated applications during execution. Ctrl-C or abort from another shell cancels the session. The runtime executes multiple actions without per-click planner calls.

```sh
clef-use doctor
clef-use models prepare --python python3.11
clef-use install-mcp codex
clef-use install-mcp hermes
clef-use install-mcp omp
clef-use run 'In the open Calculator, compute 123 * 456' --success 'Calculator shows 56088'
clef-use status
clef-use abort
clef-use update
```

[Installation](INSTALL.md) | [MCP](MCP.md) | [Harness](HARNESS_SETUP.md)

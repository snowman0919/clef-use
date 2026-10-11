# Harness setup

For managed MCP **and Agent Skills**, use the [agent setup guide](AGENT_GUIDE.md).
Choose the harness you use: replace `codex` below with `hermes` or `omp`. The managed integration installs MCP and the selected guides together. Restart the harness, then inspect each verification stage; `NOT_RUN` is not task success.

The integration preserves unrelated servers/comments and reports modified entries as conflicts. Preview with `--dry-run`; select nonstandard homes/profiles through the environment described in the agent guide. Use `--command-path` for an absolute executable path. After restarting, discover six tools including read-only `computer_capabilities`. Windows harnesses that cannot launch CMD wrappers should select the active version's `Scripts/clef-use.exe`.

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

### Codex

`~/.codex/config.toml` (`CODEX_HOME`):

```toml
[mcp_servers.clef-use]
command = "/absolute/path/to/clef-use"
args = ["mcp"]
tool_timeout_sec = 3600
```

### Hermes

`~/.hermes/config.yaml` (`HERMES_HOME`):

```yaml
mcp_servers:
  clef-use:
    command: /absolute/path/to/clef-use
    args: [mcp]
    timeout: 3600
```

### OMP

`~/.omp/agent/mcp.json` (`PI_CONFIG_DIR`, `PI_CODING_AGENT_DIR`, `OMP_PROFILE`):

```json
{"mcpServers":{"clef-use":{"command":"/absolute/path/to/clef-use",
"args":["mcp"],"type":"stdio","timeout":3600000}}}
```

[Installation](INSTALL.md) | [MCP](MCP.md)

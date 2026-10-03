# Harness の設定

他のサーバーとコメントを保持して非公開バックアップを作り、繰り返しても重複しません。異なる既存 clef-use 項目は競合として報告し、上書きしません。--dry-run で確認し、標準外の場所には --path を指定します。絶対実行パスを使い、harness を再起動して五つのツールを確認してください。Windows で CMD ラッパーを起動できない場合は有効バージョンの Scripts/clef-use.exe を使い、更新後に再登録してください。

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

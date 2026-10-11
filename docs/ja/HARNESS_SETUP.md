# Harness の設定

MCP と Agent Skills の管理には [エージェント設定ガイド](AGENT_GUIDE.md)を使ってください。
使用する harness を選び、必要に応じて下記の `codex` を `hermes` または `omp` に置き換えてください。管理対象の統合は MCP と選択したガイドを一緒にインストールします。harness を再起動して各検証段階を確認してください。`NOT_RUN` はタスク成功ではありません。

統合は他のサーバーとコメントを保持し、変更済みの項目を競合として報告します。`--dry-run` で確認し、標準外の home/profile はエージェントガイドの環境変数で選択してください。絶対実行パスは `--command-path` で指定します。再起動後、読み取り専用の `computer_capabilities` を含む六つのツールを確認してください。Windows で CMD ラッパーを起動できない harness は有効バージョンの `Scripts/clef-use.exe` を選択してください。

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

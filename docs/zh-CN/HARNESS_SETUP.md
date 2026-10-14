# Harness 设置

请使用[代理设置指南](AGENT_GUIDE.md)一起管理 MCP 与 Agent Skills。
选择要使用的 harness，按需把下方 `codex` 换成 `hermes` 或 `omp`。受管集成一起安装 MCP 和所选指南。重启 harness 后逐项检查验证阶段；`NOT_RUN` 不表示任务成功。

集成保留其他服务器与注释，并把已修改条目报告为冲突。用 `--dry-run` 预览；按代理指南通过环境变量选择非标准 home/profile。用 `--command-path` 指定绝对可执行路径。重启后确认发现六个工具，包括只读 `computer_capabilities`。Windows harness 如果不能启动 CMD 包装器，请选择活动版本的 `Scripts/clef-use.exe`。

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

0.1.36 使用新安装的可执行文件更新已有托管注册。用户修改过的指南或 MCP
注册会报告为冲突并保留。手动更新可通过 `--command-path` 指定可执行文件。

Codex 实时验证保留其他服务器的 transport，识别经 shell 转义的 Windows 指南
完整路径，并保存私有 stdout/stderr 跟踪以诊断失败。capability 发现与只读
facade 公布实际 MCP 效果，并遵守现有审批策略。被拒绝的调用判定为调用失败。
发现、指南加载、工具调用与 GUI 任务验证分别判定。

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

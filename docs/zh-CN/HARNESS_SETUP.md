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

0.1.31 候选版修复了配置其他 MCP 服务器时实时验证出现的 `invalid transport`。
重试前请确认安装的构建，不要为了通过验证而删除其他服务器配置。发现、指南加载、
工具调用与 GUI 任务验证仍是独立结果。

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

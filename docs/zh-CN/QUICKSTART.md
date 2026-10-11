# 快速开始

在受控桌面中将计算器置于前台。执行时不要操作其他应用。Ctrl-C 或另一终端的 abort 可取消。运行时自主执行多个动作，无需每次点击都调用规划器。

选择要使用的 harness，按需把下方 `codex` 换成 `hermes` 或 `omp`。受管集成一起安装 MCP 和所选指南。重启 harness 后逐项检查验证阶段；`NOT_RUN` 不表示任务成功。

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

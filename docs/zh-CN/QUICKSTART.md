# 快速开始

在受控桌面中将计算器置于前台。执行时不要操作其他应用。Ctrl-C 或另一终端的 abort 可取消。运行时自主执行多个动作，无需每次点击都调用规划器。

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

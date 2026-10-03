# クイックスタート

管理されたデスクトップで電卓を前面に置いてください。実行中は他のアプリを操作しないでください。Ctrl-C または別シェルの abort でキャンセルします。ランタイムはクリックごとに計画側を呼ばず複数操作を自律実行します。

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

# クイックスタート

管理されたデスクトップで電卓を前面に置いてください。実行中は他のアプリを操作しないでください。Ctrl-C または別シェルの abort でキャンセルします。ランタイムはクリックごとに計画側を呼ばず複数操作を自律実行します。

使用する harness を選び、必要に応じて下記の `codex` を `hermes` または `omp` に置き換えてください。管理対象の統合は MCP と選択したガイドを一緒にインストールします。harness を再起動して各検証段階を確認してください。`NOT_RUN` はタスク成功ではありません。

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

# MCP の利用

すべての harness は同じ clef-use mcp サーバーを使います。computer_run は goal、success_conditions、constraints、max_steps、confidence_threshold を受け取り、text_inputs で正確な文字列を指定します。構造化した状態を返します。computer_continue は元の予算内で介入が必要なセッションを再開します。computer_observe は最新セッション観測を返し、include_image は PNG を要求します。computer_status は状態確認、computer_abort はキャンセルです。画像とラベルに機密情報が含まれる可能性があります。

```json
{"mcpServers":{"clef-use":{"command":"clef-use","args":["mcp"]}}}
```

[Canonical MCP reference](../MCP.md) | [Harness](HARNESS_SETUP.md)

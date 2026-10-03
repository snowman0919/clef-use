# MCP 使用

所有 harness 使用同一个 clef-use mcp 服务器。computer_run 接受 goal、success_conditions、constraints、max_steps、confidence_threshold；text_inputs 提供精确字符串。结果为结构化状态。computer_continue 在原预算内恢复需要介入的会话。computer_observe 返回最近会话观察，include_image 请求 PNG。computer_status 查询状态，computer_abort 取消。图像和标签可能包含敏感信息。

```json
{"mcpServers":{"clef-use":{"command":"clef-use","args":["mcp"]}}}
```

[Canonical MCP reference](../MCP.md) | [Harness](HARNESS_SETUP.md)

Observe 在执行空闲时刷新屏幕和对象。执行期间用 `observation_fresh=false` 标明缓存数据。可选 PNG 与对象属于同一次观察，不消耗决策预算。

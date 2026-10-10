# MCP 使用

所有 harness 使用同一个 clef-use mcp 服务器。computer_run 接受 goal、success_conditions、constraints、max_steps、confidence_threshold；text_inputs 提供精确字符串。结果为结构化状态。computer_continue 在原预算内恢复需要介入的会话。computer_observe 返回最近会话观察，include_image 请求 PNG。computer_status 查询状态，computer_abort 取消。图像和标签可能包含敏感信息。

```json
{"mcpServers":{"clef-use":{"command":"clef-use","args":["mcp"]}}}
```

[Canonical MCP reference](../MCP.md) | [Harness](HARNESS_SETUP.md)

Observe 默认在执行空闲时刷新屏幕和对象。执行期间用 `observation_fresh=false` 标明缓存数据。可选 PNG 与对象属于同一次观察，不消耗决策预算。

诊断历史可用 `computer_observe(session_id="...", refresh=false)` 或
`clef-use observe --cached --session-id ...`。只读取指定会话已记录的观察，
不截图、不运行 parser、不初始化 runtime，也不启动或重启服务。没有记录时
观察/frame 引用为 null，且不生成图像。不支持缓存模式的服务会在 observe 前
被拒绝；capability 检查和读取绑定同一 endpoint。缓存不是新的输入或完成
证据。提交新输入前仍需默认 fresh observe，并保持原有安全/完成检查。

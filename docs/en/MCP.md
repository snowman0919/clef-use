# MCP usage

Every harness uses the same clef-use mcp server. computer_run accepts goal, success_conditions, constraints, max_steps and confidence_threshold; text_inputs supplies exact values. It returns structured status. computer_continue resumes an escalation within the original budget. computer_observe returns the latest session observation; include_image requests PNG content. computer_status polls and computer_abort cancels. Images and labels may contain sensitive information.

```json
{"mcpServers":{"clef-use":{"command":"clef-use","args":["mcp"]}}}
```

[Canonical MCP reference](../MCP.md) | [Harness](HARNESS_SETUP.md)

Observe refreshes the screen and objects while idle. During execution it returns cached data with `observation_fresh=false`; optional PNG and objects belong to the same observation. It does not consume the decision budget.

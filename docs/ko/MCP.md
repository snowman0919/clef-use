# MCP 사용

모든 harness는 동일한 clef-use mcp 서버를 사용합니다. computer_run은 goal, success_conditions, constraints, max_steps, confidence_threshold를 받고 text_inputs로 정확한 문자열을 전달합니다. 결과는 구조화된 상태입니다. computer_continue는 원래 예산 안에서 개입이 필요한 세션을 재개합니다. computer_observe는 최신 세션 관측을 반환하고 include_image는 PNG를 요청합니다. computer_status는 상태 확인, computer_abort는 취소입니다. 이미지와 라벨에 민감한 정보가 있을 수 있습니다.

```json
{"mcpServers":{"clef-use":{"command":"clef-use","args":["mcp"]}}}
```

[Canonical MCP reference](../MCP.md) | [Harness](HARNESS_SETUP.md)

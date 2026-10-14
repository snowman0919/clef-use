# MCP 사용

모든 harness는 동일한 clef-use mcp 서버를 사용합니다. computer_run은 goal, success_conditions, constraints, max_steps, confidence_threshold를 받고 text_inputs로 정확한 문자열을 전달합니다. 결과는 구조화된 상태입니다. computer_continue는 원래 예산 안에서 개입이 필요한 세션을 재개합니다. computer_observe는 최신 세션 관측을 반환하고 include_image는 PNG를 요청합니다. computer_status는 상태 확인, computer_abort는 취소입니다. 이미지와 라벨에 민감한 정보가 있을 수 있습니다.

먼저 읽기 전용 `computer_capabilities`로 설치 버전, 실제 schema와 제한을 확인하세요. run/continue의 선택적 typed `operation`은 등록된 로컬 절차를 선택합니다. 기본 Blender 실행은 신뢰할 수 있는 상태 제공자가 없으면 차단됩니다. 가이드 설치와 검증 단계는 [에이전트 설정](AGENT_GUIDE.md)을 참고하세요.

```json
{"mcpServers":{"clef-use":{"command":"clef-use","args":["mcp"]}}}
```

[Canonical MCP reference](../MCP.md) | [Harness](HARNESS_SETUP.md)

Observe는 기본적으로 실행이 쉬고 있을 때 화면과 객체를 갱신합니다. 실행 중에는 `observation_fresh=false`로 캐시 여부를 표시합니다. 선택적 PNG와 객체는 동일한 관측에 속하며 결정 예산을 사용하지 않습니다.

진단용 기록 조회는 `computer_observe(session_id="...", refresh=false)` 또는
`clef-use observe --cached --session-id ...`를 사용합니다. 새 capture/parser,
런타임 초기화나 서비스 시작·재시작 없이 해당 세션의 기존 관측만 반환합니다.
기록이 없으면 관측·frame 참조는 null이며 이미지를 만들지 않습니다. 미지원
서비스는 갱신 호출 전에 거절하며, capability 확인과 조회는 같은 endpoint에
묶입니다. 캐시는 최신 입력·완료 증거가 아닙니다. 새 입력 전에는 기본 fresh
observe를 사용하고 원래의 안전·완료 검증을 유지해야 합니다.

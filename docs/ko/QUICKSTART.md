# 빠른 시작

통제된 데스크톱에서 계산기를 전면에 놓으세요. 실행 중 다른 앱을 사용하지 마세요. Ctrl-C 또는 다른 셸의 abort로 취소합니다. 런타임은 클릭마다 상위 계획자를 호출하지 않고 여러 액션을 내부에서 실행합니다.

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

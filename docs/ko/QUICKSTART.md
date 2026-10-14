# 빠른 시작

통제된 데스크톱에서 계산기를 전면에 놓으세요. 실행 중 다른 앱을 사용하지 마세요. Ctrl-C 또는 다른 셸의 abort로 취소합니다. 런타임은 클릭마다 상위 계획자를 호출하지 않고 여러 액션을 내부에서 실행합니다.

사용할 harness를 하나 선택하고 아래 `codex`를 필요에 따라 `hermes` 또는 `omp`로 바꾸세요. 관리형 통합은 MCP와 선택한 가이드를 함께 설치합니다. harness를 다시 시작한 뒤 검증 단계를 각각 확인하세요. `NOT_RUN`은 작업 성공이 아닙니다.

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

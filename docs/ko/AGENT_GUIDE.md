# 에이전트 설치·사용·복구

runtime wheel에는 지침 전용 공통 스킬 `clef-use`, `clef-use-blender`,
`clef-use-diagnostics`가 포함됩니다. 기본 선택은 core와 diagnostics이며
Blender는 명시적으로 선택합니다. 적용 전에 변경 경로를 미리 확인하세요.
선택한 대상만 변경합니다. 최초 무인 설치는 `--integrate codex|hermes|omp|all`
없이 새 하네스를 등록하지 않습니다. 모델 준비는 별도 선택입니다.

<!-- clef-use:commands -->
operation의 `SUCCEEDED`는 typed effect 검증입니다. 자연어 목표는 별도의 fresh
`ASSESS`가 필요하므로 세션은 `NEEDS_REPLAN`을 반환합니다. 하네스 검증의
`--trigger natural|explicit|negative|native`로 모델 트리거와 native adapter를 구분합니다.

```sh
clef-use capabilities --json
clef-use capabilities --detail --json
clef-use capabilities --operation-id numeric_transform --json
clef-use integrate codex --dry-run
clef-use integrate codex --scope user --skills core --skills blender --skills diagnostics
clef-use integrate hermes --scope user
clef-use integrate omp --scope user
clef-use integrations status --json
clef-use integrations verify codex --live --read-only
clef-use integrations remove codex --dry-run
clef-use integrations refresh --managed-only
```

현재 schema를 발견한 뒤 검증 가능한 작은 목표를 제출합니다. 정확한 문자를
지정하고 단축키와 구분하세요. keymap을 추측하지 마세요. `ASSESS`는 입력하지
않습니다. 과거 관측은 새 pointer 권한이나 최종 완료 증거가 아닙니다. 로컬
operation은 typed 상태 기계이며 Agent Skill의 자연어 지침과 분리됩니다.
신뢰할 수 있는 로컬 관측기가 editor·selection·mode·IME·keymap 상태를 확인해야
입력합니다. 알 수 없는 상태는 차단합니다. 기본 screenshot 관측기는 Blender의
숨은 상태를 확정할 수 없습니다. API 보조 fixture 통과는 pixels-only 통과가 아닙니다.

기본 설치는 screenshot과 제공 가능한 native window identity만 사용합니다.
신뢰할 수 있는 Blender application provider와 공개 provider 설정 경로는 포함하지
않습니다. 따라서 등록된 6개 operation은 필요한 검증 상태가 없어 모두 `BLOCKED`를
반환합니다. discovery는 구현된 schema와 기본 설치의 실행 가능 여부를 구분하며,
실제 `READY` 상태를 주장하지 않습니다. 이 절차들은 통제된 `API_ASSISTED` Blender
fixture에서만 검증했습니다. 일반 production provider는 미완료 요구사항입니다.
알 수 없는 focus·IME·popup 상태를 가정으로 대체하지 마세요.

typed operation 세션을 이어가려면 명시적인 `operation` 요청이 필요합니다
(`clef-use continue ... --operation '<JSON>'`). planner 지침만으로 이전 효과를
반복하지 않습니다. 원래 목표 전체를 확인할 때는 `operation` 없이
`execution_mode="ASSESS"`인 새 `computer_run` 계약을 만드세요. CLI에서는
`clef-use run "Verify the complete original goal" --mode ASSESS`를 사용합니다.

`INSTALLED`, `DISCOVERED`, `LOADED`, `INVOKED`, `TASK_VERIFIED`를 별도로 기록합니다.
파일 복사·도구 목록·스킬 이름 응답만으로 다음 단계를 통과하지 않습니다.
live 검증은 읽기 전용 도구만 제공하는 실제 하네스의 새 세션을 실행합니다.
provider 인증 실패 시 로드·호출은 `NOT_RUN`으로 남습니다.

`MODIFIED`·`CONFLICT`는 사용자 편집을 보존하고 통합 상태 디렉터리에 비교본을
남깁니다. 명시적으로 비활성화한 항목을 켜지 않습니다. 업데이트 후 capability
버전을 확인하고 캐시된 클라이언트를 다시 로드하세요. 제거는 마지막 관리본과
일치하는 항목만 대상으로 합니다. Hermes project scope는 지원하지 않으므로 선택한
user profile을 사용합니다. 스킬을 옮기기 전에 source·shadow 상태를 확인하세요.

자신의 세션만 중단하고 입력 해제를 확인하세요. 정확한 Unicode clipboard 삽입과
IME 조합은 별개입니다. IME가 활성 상태이거나 불명이면 단축키를 차단합니다.
watchdog 복구에는 OS 권한과 입력 확인 시점에 따른 한계가 있습니다.
현재 측정으로 통과한 100ms profile이나 출하 gate 성공을 주장하지 않습니다.
[실행 증거](../EXECUTION_STATUS.md)와 [acceptance](../../ACCEPTANCE.yaml)를 확인하세요.

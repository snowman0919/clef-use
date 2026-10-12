# 에이전트 설치·사용·복구

runtime wheel에는 지침 전용 공통 스킬 `clef-use`, `clef-use-blender`,
`clef-use-diagnostics`가 포함됩니다. 기본 선택은 core와 diagnostics이며
Blender는 명시적으로 선택합니다. 적용 전에 변경 경로를 미리 확인하세요.
선택한 대상만 변경합니다. 최초 무인 설치는 `--integrate codex|hermes|omp|all`
없이 새 하네스를 등록하지 않습니다. 모델 준비는 별도 선택입니다.

편집뿐 아니라 읽기 전용 메뉴·상태 평가에도 Blender 스킬을 로드하세요.
`references/` 파일은 해당 스킬에 속합니다. Hermes에서는
`skill_view(name="clef-use", file_path="references/API_BASELINE.md")`로 기준 API를 읽습니다.

OMP의 `PI_CONFIG_DIR`는 HOME 기준 상대 경로 이름이며 기본값은 `.omp`입니다.
절대 경로의 기본 agent 디렉터리는 `PI_CODING_AGENT_DIR`로 지정하세요.
`OMP_PROFILE`을 빈 값이나 `default`로 지정하면 `PI_PROFILE`보다 우선하여 기본 프로필을 선택합니다.

등록된 실행 경로가 고정된 이전 설치본이면 `refresh`는 그 경로를 보존하고
새 지침과의 불일치를 거부합니다. `--command-path`도 기존 등록을 덮어쓰지
않습니다. 먼저 관리된 항목 제거를 `--dry-run`으로 검토하고, 수정되지 않은
관리본만 제거한 뒤 현재 실행본의 `--command-path`로 다시 등록하세요.
사용자 수정이나 비활성화 항목의 충돌은 별도로 보존됩니다.

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
검증된 상태가 있으면 guard는 버전 이름뿐 아니라 실제 keymap 내용도 비교합니다.
viewport 제스처 전과 도중에 editor 영역을 재확인하며, 영역이 바뀌면 중단하고 소유 입력을 해제합니다.
view 기준도 native 제스처 버튼 입력이 확인될 때까지 유지돼야 합니다. 그 전에 발생한
독립적인 view 변경을 성공으로 집계하지 않으며, 버튼 확인 뒤 drag의 view 변경은
나머지 guard를 유지한 상태에서 허용합니다.
수치 transform은 이동·회전·scale의 XYZ 전체 readback이 필요합니다. 입력 전에는
transform 문맥, 진입 전에는 초기 값, commit 전에는 검증한 preview를 재확인합니다.
일부 성분만으로 나머지 축의 보존을 판정하지 않습니다. property 편집 후에는 관측한
모든 필드와 객체 ID를 비교하며, 관측하지 않은 필드의 보존까지 확정하지 않습니다.
숫자 literal은 요청한 float 값을 보존합니다. 앱의 실제 readback도 요청 tolerance를
만족해야 합니다.
상태를 바꾸는 operation과 소유 modal 취소에는 완전하고 안정적인
`selection_identities`가 필요합니다. Blender는 프로세스 범위의 공개 `session_uid`로
객체를 구분합니다. 이름을 바꿔도 ID는 유지되며, 같은 이름의 다른 객체로 교체되면
추가 입력을 차단합니다. ID가 없으면 불명 상태를 유지합니다. observer는 위치와
scale의 X/Y/Z 속성도 제공합니다. 사용 전 operation registry v6를 발견하세요.
수치 이동은 완전한 최신 `scene_units`를 요구하고, 입력·readback·소유 modal 취소까지
같은 scene 변환을 유지합니다. 단위 이름만 같아도 scene 배율은 바뀔 수 있습니다.
amount/readback은 검증된 operation 단위를 유지하며 NONE은 원시 값입니다. 변환이
없거나 바뀌면 추가 입력·성공을 차단합니다. 회전·scale에는 길이 단위를 요구하지 않습니다.
각도 readback은 DEGREES/RADIANS 선언과 일치해야 하며, exact-property 좌표는 원시 값입니다.
위치 `property_edit.value`는 Blender 단위의 원시 좌표입니다. 최신 `scene_units`
근거로 명시적 미터 입력을 계산하고 입력·readback 동안 고정합니다. 단위가 없거나
바뀌면 입력 또는 성공 판정을 멈춥니다. scale 값은 무차원입니다. 표시 단위가
요청한 원시 좌표를 재해석하지 않으며, 실제 readback은 원래 tolerance를 만족해야 합니다.
신뢰할 수 있는 로컬 관측기가 editor·selection·mode·IME·keymap 상태를 확인해야
입력합니다. 알 수 없는 상태는 차단합니다. 기본 screenshot 관측기는 Blender의
숨은 상태를 확정할 수 없습니다. API 보조 fixture 통과는 pixels-only 통과가 아닙니다.
캡처에서 얻은 좌표와 foreground는 캡처 시각을 유지합니다. 느린 캡처나 처리가 해당
상태의 수명을 갱신하지 않으며, provider가 별도로 관측한 값은 자체 시각으로 판정합니다.
Windows 문자 입력은 전송 전에 UTF-16을 검증하고, 각 native 단위마다 현재 guard를
재확인합니다. 상태 관측 뒤에도 취소·deadline을 다시 확인합니다. X11에서는 붙여넣기
시도 전 취소가 확정되면 소유 modifier를 먼저 해제하고, native ACK 뒤에 지원되는
이전 클립보드 형식을 복원합니다. 사용자의 동시 복사는 보존합니다. 붙여넣기가 이미
전달됐을 가능성이 있으면 대기 중인 paste를 위해 문자열을 유지하며, 복원 ACK가
없으면 미해결 상태로 보고합니다.
legacy X11 키보드 입력도 암시적인 Shift를 포함해 누르기 전에 현재 바인딩을 검증합니다.
캐시된 바인딩이 바뀌면 입력을 거부합니다. 해제에는 확인된 물리 키코드를 사용하며,
외부에서 이미 누른 키는 해제하지 않습니다.
Blender의 view 효과는 완전하고 모호하지 않은 단일 viewport의 실제 view matrix와
perspective mode로 확인합니다. region·레이아웃·projection만 바뀌면 orbit/pan 효과로
판정하지 않으며, pose가 없거나 quad view가 모호하면 불명 상태를 유지합니다.

기본 provider는 `NONE`이며 screenshot과 native window identity만으로 Blender의
숨은 상태를 확정하지 않습니다. Linux X11에서는 선택적으로 읽기 전용 Blender
observer를 설정할 수 있습니다. `clef-use blender-observer-script`가 출력하는 설치
경로를 허용된 Blender 실행 파일에 전달하세요. private 상위 경로 아래 아직 존재하지
않는 새 디렉터리를 지정하면 스크립트가 private 디렉터리와 socket을 만듭니다.
실행 중인 기존 Blender에 자동으로 연결하지 않습니다.

```sh
clef-use blender-observer-script
blender --python "/absolute/installed/blender_observer.py" -- --clef-state-dir "/absolute/private/new-observer"
```

runtime의 `config.toml` 최상위에 다음을 설정하세요. 기본 경로는
`~/.config/clef-use/config.toml`이며 `CLEF_USE_CONFIG`로 다른 파일을 선택할 수 있습니다.

```toml
blender_state_socket = '/absolute/private/new-observer/state.sock'
```

listener는 Blender의 첫 UI timer에서 시작합니다. Unix `SO_PEERCRED`, XRes의
kernel process identity, 크기가 일치하는 유일한 RNA window/client, native foreground
focus를 확인해야 상태를 연결합니다. window·selection·object mode·원시 transform/unit·
viewport·관찰된 modal operator를 읽으며 scene을 변경하거나 operator를 실행하지
않습니다. popup·text focus·IME·유효 keymap·전체 busy/idle 상태는 여전히 알 수 없습니다.
빈 operator 목록도 부재 증거가 아닙니다. 이 부분 관측기를 설정해도 필요한 검증 상태가
없으면 6개 operation 모두 `BLOCKED`를 반환합니다.

`active_tool`은 독립적으로 연결한 native context mode에 설정된 VIEW_3D workspace
도구와 workspace·관찰된 area ID를 제공합니다. 누락되거나 모호하면 UNKNOWN입니다.
focused editor와 실제 dispatch도 UNKNOWN으로 유지하며, 이 값만으로 입력을 허용하지
않습니다. 관측기는 초기화된 참조만 읽고 도구를 생성·갱신하지 않으며, 128개 초과를 거부합니다.

`keymap_inventory`는 병합된 사용자 키맵의 관련 바인딩, 중복·비활성 항목,
tri-state modifier(`-1`은 any), 내용 digest를 보존합니다. 이는 원시 목록이며
실제 dispatch를 나타내는 `keymap`이나 `keymap_version`이 아닙니다.
`editor_layout`은 area/region을 화면 pixel과 capture 좌표로 변환합니다. 숨겨지거나
잘리거나 capture 밖인 영역은 normalized box가 없습니다. focused editor, popup 소유권,
검증된 gesture surface를 확정하지 않습니다. 키맵 한도를 넘으면 바인딩을 버리지 않고
snapshot 전체를 거부합니다.
Linux 입력 좌표는 여러 모니터를 합친 X11 root 크기가 아닌 캡처한 모니터 크기를
사용합니다. capture/input 범위가 불일치하면 Blender 상태 연결을 거부합니다.

새 observe 응답은 `compiled_state`, `state_provider_status`, `state_pixel_association`을
제공할 수 있습니다. 상태는 별도 observation ID를 가지며 capture 근처에서 parse 전에
수집되고 parse 중 만료될 수 있습니다. `FOREGROUND_WINDOW_ONLY` 연결은 pixel과
동시에 관찰한 scene 증거가 아닙니다. discovery는 schema와 기본 실행 가능 여부를
설명하며 live `READY`를 주장하지 않습니다. 기존 `API_ASSISTED` fixture 검증은 이 새
production 경로의 검증이 아니며, 전체 production operation 지원은 미완료입니다.
알 수 없는 입력 문맥을 가정으로 대체하지 마세요.

typed operation 세션을 이어가려면 명시적인 `operation` 요청이 필요합니다
(`clef-use continue ... --operation '<JSON>'`). planner 지침만으로 이전 효과를
반복하지 않습니다. 원래 목표 전체를 확인할 때는 `operation` 없이
`execution_mode="ASSESS"`인 새 `computer_run` 계약을 만드세요. CLI에서는
`clef-use run "Verify the complete original goal" --mode ASSESS`를 사용합니다.

`INSTALLED`, `DISCOVERED`, `LOADED`, `INVOKED`, `TASK_VERIFIED`를 별도로 기록합니다.
파일 복사·도구 목록·스킬 이름 응답만으로 다음 단계를 통과하지 않습니다.
live trigger 검증은 읽기 전용 도구를 제공하는 실제 하네스의 새 세션을 실행합니다.
provider 인증 실패 시 로드·호출은 `NOT_RUN`으로 남습니다.
작업 검증은 격리된 대상에 허용된 입력을 실행하고 외부의 새 상태와 입력·프로세스
정리를 별도로 확인해야 합니다. 비공개 API 보조 작업 통과는 production 실행
가능 여부나 전체 목표 완료를 입증하지 않습니다.

`MODIFIED`·`CONFLICT`는 사용자 편집을 보존하고 통합 상태 디렉터리에 비교본을
남깁니다. 명시적으로 비활성화한 항목을 켜지 않습니다. 업데이트 후 capability
버전을 확인하고 캐시된 클라이언트를 다시 로드하세요. 제거는 마지막 관리본과
일치하는 항목만 대상으로 합니다. Hermes project scope는 지원하지 않으므로 선택한
user profile을 사용합니다. 스킬을 옮기기 전에 source·shadow 상태를 확인하세요.

로컬 요청은 실행 파일 버전, runtime protocol, API 지문에 연결됩니다. 오래된
클라이언트는 새 서비스를 종료하거나 제어할 수 없습니다. 불일치가 나면 현재 실행
파일과 MCP 세션을 다시 로드하세요. 새 클라이언트는 유휴 상태의 이전 서비스를
교체할 수 있지만, 입력 실행이나 modal 복구가 남아 있으면 교체를 거부합니다.
업데이트 전부터 실행 중인 세션은 보존된 동일 버전 실행 파일로 먼저 완료하거나
중단하세요. 변경할 수 없는 구버전 클라이언트는 서버의 재로드 안내 대신 일반적인
거부 메시지만 표시할 수 있습니다. 같은 버전의 protocol·schema가 다르면 유휴
서비스를 명시적으로 종료한 뒤 다시 로드해야 하며 자동 재시작하지 않습니다.

자신의 세션만 중단하고 입력 해제를 확인하세요. 정확한 Unicode clipboard 삽입과
IME 조합은 별개입니다. IME가 활성 상태이거나 불명이면 단축키를 차단합니다.
X11의 좌·가운데·우 버튼과 스크롤 방향은 현재 OS 포인터 매핑을 따릅니다.
비활성화된 논리 버튼은 입력을 거부합니다. 정상 해제·독립 abort·guardian 복구는
누를 때 확인한 물리 버튼을 해제합니다.
X11에서는 ASCII를 포함한 문자 삽입에 명시적 clipboard 방식을 사용합니다. 키 이벤트는
조합이 시작되기 전에도 IME로 전달될 수 있습니다. clipboard 전송 확인과 입력 필드의
결과 확인은 별개입니다. 기존 clipboard 형식을 보존할 수 없으면 입력 전에 거부합니다.
수신 전에 중단되면 이미 전달된 붙여넣기를 위해 문자를 전송 완료 또는 다른 복사까지
유지하며, 이전 데이터를 일찍 복원하지 않습니다. Windows 조작은 native Unicode를 사용합니다.
watchdog 복구에는 OS 권한과 입력 확인 시점에 따른 한계가 있습니다.
Windows의 누른 키 검사는 확장 scan code와 modifier 좌우를 구분하고, 다른 키의
사용자 입력이 있으면 후속 입력을 차단합니다. 같은 virtual key를 공유하는 물리 키
(예: 두 Enter 키)의 동시 누름은 이 조회로 구분할 수 없습니다.
Windows guardian은 해제에 성공한 키·Unicode의 ACK를 제거합니다. 이후 부모 프로세스의
EOF가 와도 다른 소유자가 다시 누른 해당 입력을 오래된 ACK로 해제하지 않습니다.
decision 진단은 이미지가 제외된 실제 UTF-8 텍스트 예산 바이트 수, object·question
개수와 SDK가 보고한 입력 토큰 수를 보존합니다. `SDK_USAGE`는 1~8192의 정수이며,
누락은 `UNAVAILABLE`, 잘못된 보고 값은 `INVALID`로 표시하고 토큰 수는 null입니다.
이 수치는 올바른 대상의 coverage, 보정된 신뢰도나 모델 지연 시간을 측정하지 않습니다.
decision 후보는 operation과 관측 target ID를 보존해 같은 이름의 control을 위치로
구분할 수 있게 합니다. 대상 연결의 보존이며, 올바른 선택을 보증하거나 신뢰도 guard를
완화하는 변경은 아닙니다.
정확한 문자열 입력 후보는 같은 이름의 입력란을 포함해 일치하는 관측 입력란을 각각 유지합니다.
이 대안이 설정된 동작 예산을 넘으면 구조화 실행은 모델 호출과 입력 전에 재계획을 요청합니다.
첫 입력란이 맞다고 가정하지 말고 대상 범위를 좁히세요.
대상 근거가 없거나 실행 대상이 40개를 넘으면 좌표 근거를 조용히 제거하는 대신 거부합니다.
모든 기회에 대한 사전 적격성·정책 증거가 없으면 반응 coverage는 null·`NOT_MEASURED`로
남습니다. 빠르게 성공한 입력만으로 출하 gate를 통과하지 않습니다. 실제 OS 이벤트
시각과 backend ACK는 구분합니다.
현재 측정으로 통과한 100ms profile이나 출하 gate 성공을 주장하지 않습니다.
[실행 증거](../EXECUTION_STATUS.md)와 [acceptance](../../ACCEPTANCE.yaml)를 확인하세요.

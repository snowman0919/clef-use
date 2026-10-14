# 에이전트 설치·사용·복구

불변 .49 CI의 15개 플랫폼 설치 검사와 아카이브·소스 대조가 통과했습니다.
실제 Windows .48 -> .49 업데이트, 반복 CURRENT, LIMITED 토큰의 패키지·MCP 검사와
원래 Codex explicit/natural/negative 모델 사례도 통과했습니다. 이 창 없는 검증은
GUI 작업이나 100ms 입력 지연을 증명하지 않습니다. 이전 Hermes/OMP 실패는 유지하며
공개 배포 가드도 유지합니다. [설치본 기록](../validation/2026-10-14/windows-installed-ci-0149.json)을 확인하세요.

runtime wheel에는 지침 전용 공통 스킬 `clef-use`, `clef-use-blender`,
`clef-use-diagnostics`가 포함됩니다. 기본 선택은 core와 diagnostics이며
Blender는 명시적으로 선택합니다. 적용 전에 변경 경로를 미리 확인하세요.
선택한 대상만 변경합니다. 최초 무인 설치는 `--integrate codex|hermes|omp|all`
없이 새 하네스를 등록하지 않습니다. 모델 준비는 별도 선택입니다.

읽기 전용 검증은 Hermes의 native 도구 정의 factory에서 `skill_manage`를 제외합니다.
MCP 갱신과 지연 발견 목록에도 적용하고 registry 실행도 거절합니다. native Skill
reader와 원래 schema는 유지합니다. reader 사용량 metadata는 바뀔 수 있으므로 지침·설정
파일 보존을 모든 native 생성 상태 보존으로 확대하지 않습니다. OMP 검증은 임시 시작
정책으로 실제 MCP 발견 완료를 기다립니다. 저장된 설정과 선언한 모델 제한 시간은 유지합니다.

실제 .48 전용 Linux 화면의 캐시 검증은 Windows 설치본 검증과 별도로 기록합니다.
Hermes는 실행별 비공개 읽기 전용 제한 아래 캐시를 완료 증거로 쓰지 않고 새 Continue
화면을 확인했습니다. OMP의 현재 활성 세션 기본값 캐시 항목은 통과했지만, 지침 로드
전 status 호출 때문에 전체 native 사례는 FAIL입니다. 실제 status/cache를 읽은 뒤에도
명시적 ID 검증은 실패했습니다. OMP는 시작 대기 중 캐시 도구 목록을 공개할 수 있으며,
임시 `mcp.startupTimeoutMs: 0`은 실제 발견 완료를 기다립니다. 저장된 설정은 보존합니다.
이 읽기 검증은 GUI 입력 정확도나 100ms 지연을 증명하지 않습니다.
[검증 기록](../validation/2026-10-14/linux-native-cache-0148.json)을 확인하세요.

하네스 JSON 스트림은 Windows locale과 무관하게 UTF-8로 읽습니다.
runtime 호출 실패는 뒤의 capability 호출이 성공해도 검증 FAIL로 유지됩니다.
발견만으로 모델의 지침 로드나 도구 호출을 증명하지 않습니다.
파일 읽기와 공개된 guide resource는 관리된 본문 전체와 일치해야 합니다.
capability의 runtime/schema/guide 해시와 read-only 두 도구 facade도 확인합니다.
필요한 지침을 호출 후에 읽으면 검증 순서는 FAIL입니다.
먼저 시작한 runtime 호출은 나중의 지침 로드·성공·프로세스 오류 종료로 지워지지 않습니다.
네이티브 Skill catalog 발견은 runtime 호출과 구분합니다.
operation 상세 응답은 앞서 검증한 실제 목록의 해당 operation과 정확히 일치해야 합니다.
status 응답만으로 현재 capability 목록이 검증되지는 않습니다.

Codex 명령 시작 실패는 JSON command event 없이 비공개 stderr에만 남을 수 있습니다.
네이티브 runner pipe 연결 시간 초과는 뒤의 성공이나 오류 종료와 무관하게
`NATIVE_EXECUTOR_STARTUP_TIMEOUT` FAIL로 유지합니다. 보고서에는 단계, 제한 시간,
지침 읽기 시도 여부와 증거 해시만 공개합니다. 읽기 시도는 본문 로드를 증명하지
않으며, 이 오류만으로 인증 문제나 네이티브 실행기 실패 원인을 단정하지 않습니다.

MCP 연결 안내는 허가된 GUI 작업이나 명시적인 clef-use capability/schema 요청에
적용합니다. 일반 코드 질문과 runtime 접근 금지 요청에는 이 도구를 선택하지 않습니다.
읽기 전용 연결은 실제 공개한 capability/status 도구와 schema/guide resource를
안내합니다. capability 발견에는 실행 중인 GUI service가 필요하지 않습니다.
status는 기존 service/session을 읽으며 Blender의 숨은 상태를 발견하는 도구가 아닙니다.
OMP의 연결된 지침 파일은
`read(path="skill://clef-use/references/API_BASELINE.md")`처럼 소유 스킬의 네이티브
reader로 읽습니다. 이 URI를 `file://`로 바꾸지 마세요. MCP resource는 실제 reader를
발견한 뒤 사용하며, 서버 별칭이나 resource 주소를 추측하지 않습니다.

OmniParser는 upstream import 전후에 호출자의 Torch thread 예산을 보존합니다.
명시적인 단일 thread 설정도 유지하며 새 thread 설정은 필요하지 않습니다.
이 초기화 수정만으로 전체 작업 완료나 100ms 입력 지연이 검증되지는 않습니다.
실제 설치본에서 각각 독립적으로 검증하세요.

편집뿐 아니라 읽기 전용 메뉴·상태 평가에도 Blender 스킬을 로드하세요.
`references/` 파일은 해당 스킬에 속합니다. Hermes에서는
`skill_view(name="clef-use", file_path="references/API_BASELINE.md")`로 기준 API를 읽습니다.
읽기 전용 GUI capability/schema 질문에도 해당 지침을 사용합니다. Skill catalog를
발견하고 core와 해당 Blender 지침을 로드한 뒤 runtime 도구를 호출하세요.
입력을 보내지 않는 capability 요청도 도구 호출입니다.

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
숨은 상태를 확정하지 않습니다. Linux X11과 Windows에서는 선택적으로 읽기 전용 Blender
observer를 설정할 수 있습니다. `clef-use blender-observer-script`가 출력하는 설치
경로를 허용된 Blender 실행 파일에 전달하세요. private 상위 경로 아래 아직 존재하지
않는 새 디렉터리를 지정하면 스크립트가 private 디렉터리와 endpoint를 만듭니다.
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

listener는 Blender의 첫 UI timer에서 시작합니다. Linux는 Unix `SO_PEERCRED`와
XRes의 kernel process identity를 확인합니다. Windows는 명시적인 `127.0.0.1`
listener를 사용하며, `state.sock`은 Unix socket이 아닌 private NTFS port metadata입니다.
native TCP peer PID와 process token user가 foreground process와 일치해야 합니다.
두 플랫폼 모두 실제 pixel 크기가 일치하는 유일한 RNA window/client와 변경되지 않은
native foreground를 확인합니다. UI timer가 막히면 provider는 unavailable이며 idle로
판정하지 않습니다. window·selection·object mode·원시 transform/unit·
viewport·관찰된 modal operator를 읽으며 scene을 변경하거나 operator를 실행하지
않습니다. popup·text focus·IME·유효 keymap·전체 idle 상태는 여전히 알 수 없습니다.
빈 operator 목록도 부재 증거가 아닙니다. 이 부분 관측기를 설정해도 필요한 검증 상태가
없으면 6개 operation 모두 `BLOCKED`를 반환합니다.

관측기는 소유 manager의 공개 `interface_locked` Boolean을 읽을 수 있을 때 보존합니다.
native identity·window·최신성 검증을 통과한 `true`만 busy 증거인 `loading=true`로
컴파일합니다. `false`나 관측 불가는 `loading`을 UNKNOWN으로 유지합니다. 잠금이 풀려도
modal이나 다른 입력 소유자가 남아 있을 수 있으므로 이 값으로 입력을 허용하거나 idle을
판정하지 않습니다.

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
`INVOKED`는 도구의 성공 응답을 요구합니다. 전송이 완료돼도 MCP 오류이면 통과하지
않습니다. negative trigger는 실패한 도구 호출 시도도 거부하므로, 요청 거절로
불필요한 trigger를 숨길 수 없습니다.
명시적 오류는 `INVOKED=FAIL`이며, 결과가 없거나 미완료이면 `NOT_RUN`으로 남깁니다.
작업 검증은 격리된 대상에 허용된 입력을 실행하고 외부의 새 상태와 입력·프로세스
정리를 별도로 확인해야 합니다. 비공개 API 보조 작업 통과는 production 실행
가능 여부나 전체 목표 완료를 입증하지 않습니다.

`MODIFIED`·`CONFLICT`는 사용자 편집을 보존합니다. 기존 guide 충돌은 통합 상태
디렉터리에 비교본을 남깁니다. capability 조회 중 변경되거나 guide 파일이 추가·삭제되면
journal 생성 전에 적용을 중단하며, 미리보기와 변경 없는 계획도 소유권을 다시 확인합니다.
명시적으로 비활성화한 항목을 켜지 않습니다. 업데이트 후 capability
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
명시된 입력 context가 있으면 modifier gesture도 이동·누름 전에 IME 유휴와
text focus 비활성을 확인해야 합니다. 일반 포인터 gesture는 별도로 처리합니다.
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

설치된 Windows 0.1.36에서 좌·우·가운데 클릭과 제한된 영역의 Shift+좌/가운데
드래그를 실제 비텍스트 수신 창으로 검증했습니다. worker가 멈춰 있어도 취소 시
Shift와 가운데 버튼이 해제되며, 소유 worker 프로세스 종료 후에는 별도 guardian이
해제합니다. 이 검증은 소유 수신 창의 IME만 비활성화합니다. 자동 IME 발견,
Blender orbit/pan 의미나 하네스의 GUI 작업 완료를 입증하지 않습니다.

별도 설치본 0.1.36 component에서는 실제 CLI/HTTP service abort를 검증했습니다.
injector가 막힌 동안 Shift·가운데 버튼이 해제되고, 재개 후에도 취소된 injector는
추가 입력을 거부합니다. 명시적으로 등록한 session과 소유 비텍스트 수신 창을 사용한
검증이며, 전체 gesture·Blender operation admission은 아직 검증되지 않았습니다.

별도 설치본 Windows 0.1.37 component는 문서화된 debug API로 worker의 모든
스레드를 정지합니다. attach breakpoint가 보류되고 heartbeat가 멈춘 동안 별도
guardian이 6초 lease deadline에 Shift·가운데 버튼을 해제합니다. worker EOF나 부모의
해제 호출보다 먼저 native 해제를 관찰했으며, 재개 후 실제 watchdog의 취소와 추가
입력 거부도 확인했습니다. worker·guardian 종료와 정확한 포인터·foreground 복구가
통과했습니다. 이는 부분적인 입력 복구 증거이며, 전체 runtime·service operation
admission, Blender 의미, 모델 작업 완료나 지연·성능 결과를 입증하지 않습니다.

decision 진단은 이미지가 제외된 실제 UTF-8 텍스트 예산 바이트 수, object·question
개수와 SDK가 보고한 입력 토큰 수를 보존합니다. `SDK_USAGE`는 1~8192의 정수이며,
누락은 `UNAVAILABLE`, 잘못된 보고 값은 `INVALID`로 표시하고 토큰 수는 null입니다.
이 수치는 올바른 대상의 coverage, 보정된 신뢰도나 모델 지연 시간을 측정하지 않습니다.
decision 후보는 operation과 관측 target ID를 보존해 같은 이름의 control을 위치로
구분할 수 있게 합니다. 대상 연결의 보존이며, 올바른 선택을 보증하거나 신뢰도 guard를
완화하는 변경은 아닙니다.
parser 객체는 정확한 좌표와 서로 다른 action·confidence·source 근거를 각각 보존하고,
정규화 결과가 같은 기록만 중복 제거합니다. 명시한 visual primitive는 구조화 후보의
예산 계산 전에 적용하므로, 무관한 문자열 대안이 요청한 click·scroll을 밀어내지 않습니다.
정확한 문자열 입력 후보는 같은 이름의 입력란을 포함해 일치하는 관측 입력란을 각각 유지합니다.
이 대안이 설정된 동작 예산을 넘으면 구조화 실행은 모델 호출과 입력 전에 재계획을 요청합니다.
첫 입력란이 맞다고 가정하지 말고 대상 범위를 좁히세요.
대상 근거가 없거나 실행 대상이 40개를 넘으면 좌표 근거를 조용히 제거하는 대신 거부합니다.
모든 기회에 대한 사전 적격성·정책 증거가 없으면 반응 coverage는 null·`NOT_MEASURED`로
남습니다. 빠르게 성공한 입력만으로 출하 gate를 통과하지 않습니다. 실제 OS 이벤트
시각과 backend ACK는 구분합니다.
현재 측정으로 통과한 100ms profile이나 출하 gate 성공을 주장하지 않습니다.
[실행 증거](../EXECUTION_STATUS.md)와 [acceptance](../../ACCEPTANCE.yaml)를 확인하세요.

Windows 캡처는 스레드별 물리 좌표 context 안에서 native GDI를 사용하며 프로세스 전체 DPI 설정을 변경하지 않습니다. 이미 열린 창과 컨트롤의 물리 geometry를 보존해야 하며, 캡처가 이를 바꾸면 검증 실패입니다. 이 수정은 Blender popup·focus·IME·keymap 상태나 100ms 반응 성능을 입증하지 않습니다.

실제 Windows Codex 검증은 discovery·load·invoke와 GUI 작업 성공을 구분합니다. 앞선 클릭이 맞아도 tool 응답이 LOW_CONFIDENCE라면 작업은 실패입니다. 실제 후보 목록, 독립 측정한 물리 좌표 target geometry, 위젯 결과를 보존하며 호출 성공을 작업 성공으로 만들기 위해 신뢰도 가드를 낮추지 않습니다.

현재 Windows 상태 provider는 native UI Automation 근거와 선택적 Blender provider를
결합합니다. 표준 라이브러리만 사용하는 base Python worker는 준비 시 실제 PID를
증명하고 query 제한 시간은 500ms입니다. 각 결과는 query 전후의 native foreground
관측을 같은 focused UIA element, process identity, ancestor chain, bounds에 연결합니다.
지원되는 TextEdit에서 `GetActiveComposition`이 null composition과 함께 `S_OK`를
반환하면 `False`입니다. 지원하지 않는 interface, 오류, 오래되었거나 서로 맞지 않는
근거는 `UNKNOWN`으로 남습니다. 포커스 식별자는 UIA runtime ID와 물리 영역도
연결합니다. 편집 가능 여부는 enabled·non-password 속성과 별도로 등록된 TextPattern의
document range에서 읽은 명시적인 Boolean IsReadOnly 근거가 있어야 확정합니다.
TextEdit 지원만으로 이를 확정하지 않으며 문자 내용은 읽지 않습니다. 이 사실은 popup
소유권, keymap, 전체 유휴 여부나 Blender operation admission을 증명하지 않습니다.
Hermes live 검증은 native event stream을 보존하고, 설치된 하네스의 읽기 전용 session
export API로 정확히 해당 세션만 읽습니다. 전체 guide 본문과 runtime 응답은 원본
stream 바이트, session·call 식별자, 관리 contract와 일치해야 합니다. spillover는 선택한
profile과 call에 한정합니다. 잘린 preview·오류·모호한 call은 호출 성공 근거가 아니며,
전체 export를 확인할 수 없으면 `NOT_RUN`입니다. 뒤의 호출이 성공해도 앞선 실패를
보존하고, native catalog load와 모델 trigger 검증 단계를 구분합니다.
Hermes는 MCP 실행 때 부모 환경 변수를 걸러냅니다. 검증은 선택한 관리 서버의
native 메모리 등록에 읽기 전용 설정을 적용하고, 디스크 설정·인증·모델 선택·native
CLI prompt를 보존합니다. 모델 실행 전에 실제 capability/status 두 도구의 schema가
일치해야 합니다. 동시 응답은 전체 응답이나 제한된 preview가 유일하게 일치해야 하며,
동일한 prefix는 모호한 상태로 남깁니다. 효과를 발생시키는 도구 시도는 검증 실패입니다.
이는 MCP 범위의 제한입니다. native `skills` toolset에는 `skill_manage`도 있으므로
전체 프로세스의 쓰기 차단을 증명하지 않습니다. 해당 도구 시도는 검증 실패이며,
실제 관측한 호출과 허용 권한을 구분해 기록합니다.

OMP는 native 지연 등록으로 초기 도구 목록에 writer를 다시 추가할 수 있습니다.
검증은 임시 native approval overlay로 writer와 기존 비조회 허용을 거절하고,
reader의 deny/prompt와 인자별 읽기 승인 등급을 보존합니다. 전체 native SDK 결과는
크기가 제한된 비공개 파일로 읽고, guide 전체 본문·runtime/schema 계약을 대조합니다.
실패·예상 밖 호출은 이후 capability 성공이나 시간 초과로 지우지 않습니다. 관리
integration lock으로 검증을 직렬화하며 native helper 실패 뒤 모델을 시작하지 않습니다.
사용자 디스크 설정은 보존하고 overlay는 제거합니다.
[실제 Windows .41 설치](../validation/2026-10-13/windows-installed-ci-0141.json)는
CI15/15·업데이트·반복 실행을 통과했습니다. 기존 작업 실패와 수치 기준은 별개입니다.

설치된 0.1.39는 InputIR의 활성 조합 거절을 검증했지만 일반 type 우회도 재현했습니다.
별도의 immutable 설치본 0.1.40에서 정확한 Unicode, 활성 조합 중 네 경로의 입력 거절,
선택·삭제, Enter 포커스 전환, 독립 abort·복구 검증이 통과했습니다. 실제 Codex GUI
작업은 기존 실행 모드 확률 기준에서 실패했고, 브라우저 모델 작업은 parser timeout으로
실패했습니다. 입력 전달·작업 성공·100ms 성능 기준은 구분합니다.
[설치본 근거](../validation/2026-10-13/windows-installed-ci-0140.json)를 확인하세요.

Windows 모델 키보드 입력은 State Compiler와 InputIR를 거칩니다. 문자 대상은 이미
포커스된 편집 가능한 컨트롤과 일치해야 하며, type이 입력란을 암묵적으로 클릭하지
않습니다. IME·식별자·편집 가능 여부가 불명확하면 거절하고, native 단위마다 새로운
guard로 포커스와 조합 상태를 확인합니다. 키보드·modifier 입력은 관측 context와 live
guard가 필요합니다. 명시적인 Escape와 소유 입력의 복구 release는 독립적으로 유지합니다.
context가 없다는 이유로 IME가 유휴 상태라고 가정하지 않습니다.
한 번의 Enter 전달이 확인된 뒤에는 포커스가 이동할 수 있습니다. 이후 검사는 원래
native 창·프로세스·스레드를 확인하고 release와 전달 기록만 허용합니다. 전달됐지만
결과가 검증되지 않은 입력도 실행 예산을 사용하며 `NEEDS_REPLAN`으로 남깁니다.
입력 전달만으로 목표 완료를 선언하지 않습니다.

Windows native input은 입력 전 failsafe를 확인하며 PyAutoGUI를 더는 import하지
않습니다. 설치된 0.1.38에서 failsafe probe는 입력을 보내기 전에 소유 창 geometry를
`[210,210,1638,1066]`에서 `[120,120,936,609]`로 바꿨습니다. 입력 count는 0이었습니다.
같은 경로의 source 수정은 geometry를 보존했습니다. 이는 source 검증이며 설치된
0.1.38 PASS가 아닙니다. 100ms 성능 주장은 따르지 않습니다.

watchdog 스레드에서도 창 영역은 물리 좌표로 조회합니다. Windows 검증은 위젯의
입력점을 물리 영역으로 변환하고 native 수신 창의 소유권을 확인합니다. 캡처 성공만으로
입력 좌표가 올바르다고 판정하지 않습니다.
버튼 누르기와 wheel 입력 직전에는 실제 pointer 수신 창의 root가 관측한 foreground
창과 일치해야 합니다. foreground 일치만으로 다른 창에 입력할 수는 없습니다.
소유한 입력의 복구 release는 이 조건과 독립적으로 유지합니다.

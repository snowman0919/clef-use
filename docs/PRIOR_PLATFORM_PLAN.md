# 100ms급 반응을 위한 차세대 Computer-Use 플랫폼 기획서

## clef-use: 화면 선택기에서 상태 기반 통합 조작 런타임으로

**제출일:** 2026-10-11  
**문서 성격:** 현재 제품 소스 검토 + 공개 연구 조사 + 구현·검증 계획  
**검토 저장소:** `snowman0919/clef-use`  
**소스 기준:** `4c725eec736d30eda979298143cd90a61f8a22ee`  
**확인한 최신 릴리스:** `v0.1.28`  
**판정:** 부분 개선이 아니라 실행 경로의 재배치가 필요하다. 기존 V2의 안전·배포 기반은 보존한다. [G1, G2]

### 의사결정 요약

현재의 병목은 CLEF 하나의 성능이나 버튼 수만이 아니다. 어떤 편집기·모드·도구에서 무엇을 할 수 있는지 표현하지 못한 상태, 좁은 키보드·마우스 행동 공간, 직렬 화면 분석과 중복 모델 호출, 매 조작의 동기 검증이 함께 작용한다. 더 작은 모델로 교체하는 것만으로는 해결되지 않는다.

**권고안은 ‘State Compiler + Skill Runtime + 실시간 통합 입력기’다.** 상위 에이전트는 목표와 제한을 실행 가능한 스킬로 컴파일한다. 로컬 실행기는 최신 상태에 맞는 스킬 분기를 선택하고 키보드·마우스를 함께 제어한다. 전체 화면 의미 분석과 독립 품질 검증은 필요할 때만 수행한다. 모델을 매 입력 이벤트의 필수 관문으로 두지 않는다.

100ms는 단순 API 응답이나 접수 확인이 아니라 **화면/앱의 유효한 변화부터 올바른 다음 OS 입력을 내보내기까지의 반응 예산**으로 정의한다. 현재 달성했다는 주장은 하지 않는다. 대상 작업의 성공률·오입력·반응 지연·빠른 경로 적용률을 함께 검증해야 한다.

### 우선 투자 순서

**첫째,** 실제 실패를 분리하고 키보드·버튼·복합 제스처 행동 공간을 완성한다.  
**둘째,** 앱 상태 기반 스킬과 이벤트 중심 관측을 도입해 비싼 모델을 내부 반복 경로에서 뺀다.  
**셋째,** 학습된 GUI grounding, 경량 결정 모델, 추론 최적화, 안전한 사전 계산을 단계적으로 결합한다.

본 문서의 목표 수치·지연 예산·개발 일정은 제안값이다. 저장소에 기록된 측정값 및 외부 연구 결과와 구분해서 표기했다.

<!-- PAGEBREAK -->

# 1. 검토 범위와 증거의 수준

이번 검토는 GitHub 커넥터로 고정 커밋의 실행 코드·모델 문서·실패 기록·릴리스 메타데이터를 읽고, 관련 1차 연구와 공식 문서를 대조한 **읽기 전용 설계 검토**다. 사용자 컴퓨터에서 Blender를 새로 조작하거나 모델 추론·테스트를 다시 실행하지 않았다. 저장소 문서가 가리키는 비공개 원본 화면과 전체 원시 로그도 직접 재검증하지 않았다.

| 구분 | 이번에 확인한 범위 | 해석상의 경계 |
|---|---|---|
| 제품 코드 | 후보 생성, 라우팅, 직렬 실행, 모델 요청, 입력 백엔드, 검증, 설정 | 소스에서 도출한 실행 경로. 실제 설치 환경의 모든 설정까지 확인한 것은 아님 |
| 제품 측정 | d1 비교, Blender File 평가 실패, 전처리·문맥 실험, 배포 상태 문서 | 저장소 작성자의 기록. 이번 검토에서 재측정하지 않음 |
| 외부 방법론 | MCJev, GUI-Actor, ActionEngine, RTC, VeriGUI, 관련 추론·검증 문서 | 다른 하드웨어·작업의 결과를 clef-use 성능으로 전용하지 않음 |
| 제안 | 상태 컴파일러, 스킬 실행기, 입력 트랜잭션, 반응 예산, 평가·배포 계획 | 구현 및 실험으로 반증 가능한 설계 가설 |

### 유지할 제품 자산

모델별 독립 resident worker, 공통 DecisionBackend, MCP/CLI 공통 코어, 입력 소유권과 취소, 관측 프레임에 결박된 포인터, 잘못된 모델 출력의 거부, 버전 고정 및 설치·업데이트 체계는 유지할 가치가 있다. d1 어댑터는 이미 구현되어 있다. 같은 기능을 새 이름으로 다시 만드는 것은 우선순위가 아니다. [G3–G8]

### 소스와 배포의 구분

검토한 `main`의 마지막 커밋은 2026-10-10 19:46:33 UTC이며, 공개 최신 릴리스 `v0.1.28`의 게시 시점은 같은 날 18:03:21 UTC다. 이후 문서·진단 커밋을 자동으로 배포된 실행 바이너리와 동일시하지 않는다. 기존 `old/`는 동결 상태를 유지하고 새 실행 경로는 활성 V2 코어에 선택적으로 통합한다. [G1, G2, G9]

### 제품 성공의 정의

‘파일이 존재함’, ‘테스트 통과’, ‘결정 모델이 응답함’, ‘배포 완료’는 필요조건일 뿐이다. Blender의 대표 조작을 올바르게 수행하고, 빠르게 중단·복구하며, 최종 산출물 품질까지 별도로 검증되어야 실사용 가능 판정을 내린다.

<!-- PAGEBREAK -->

# 2. 현재 구현에서 발견한 우선 개선점

| 위치 | 확인한 동작 | 개선 방향 |
|---|---|---|
| `candidates.py` | 목표와 라벨의 단어 겹침 후 화면 위치 순으로 정렬하고 최대 후보 수에서 절단 | 모드·도구·목표에 따른 스킬 검색과 실행 가능성 필터. 정답 후보 포함률을 먼저 측정 |
| `router.py` | 후보 수, 명시 영역, 정확한 라벨 일치, 결정 불확실성으로 경로 선택 | 앱 상태와 수행할 연산을 먼저 결정. 숫자가 적다는 사실을 의미적 단순함으로 간주하지 않기 |
| `runtime.py` / `_choose` | VISUAL/CANVAS에서 사전 평가, grounding, 재평가가 직렬로 이어질 수 있음 | 상태 변경·위험·마일스톤별 평가. 매 미세 입력의 중복 모델 호출 제거 |
| `runtime.py` / `_parse` | 라우팅 이전에 파서를 실행. 전체 이미지가 완전히 같을 때만 캐시 적중 | 이벤트·영역 변경을 먼저 판단. 필요한 관측기만 실행 |
| `backends.py` | 화면을 PNG→Base64→JSON으로 모델 프로세스에 전달 | 로컬 공유 프레임과 crop 참조. 이미지 전송은 외부 인터페이스에서만 직렬화 |
| `verification.py` | 50ms 간격, 연속 안정 비교 중심 | 이벤트와 스킬별 준비 조건. 동적 화면을 일괄 ‘안정될 때까지’ 기다리지 않기 |
| `DesktopAction` | 제한된 키/단축키, 포인터는 왼쪽 버튼 중심 | 키보드·오른쪽/가운데 버튼·보조 키·시간 순서가 있는 통합 입력 계약 |
| 시각 백엔드 | frozen SigLIP2의 zero-shot patch readout 및 선택적 소형 학습 head | 학습된 GUI grounding과 비교. 현재 heatmap을 범용 GUI 이해로 과대평가하지 않기 |

이 표는 소스 동작에 대한 요약이다. 각 문제가 실제 지연·오류에 기여하는 양은 재현 실험으로 분리해야 한다. [G4–G8, G10, G11]

### 추가로 중요한 두 가지

**접근성 정보는 현재 ‘지원 가능한 표현’과 ‘실제로 수집되는 정보’가 다르다.** 라우터는 AX/DOM/UIA 출처를 인식하지만 기본 runtime factory는 OmniParser를 연결한다. 신뢰 가능한 네이티브 정보 공급기를 실제 연결하고, 앱별 정보 노출 범위를 확인해야 한다. [G5, G7]

**입력 지연은 모델 지연과 독립적이다.** 비-Windows 경로의 일부 PyAutoGUI 호출은 기본 pause를 우회하지 않는다. 공식 기본값은 호출 뒤 0.1초다. 실제 `PAUSE`·플랫폼 지연값부터 기록해야 하며, 이 지연을 제거하더라도 독립 긴급 정지·입력 해제 기능을 없애서는 안 된다. [G7, R10]

<!-- PAGEBREAK -->

# 3. 실제 실패 기록이 말해 주는 것

## 3.1 선택지가 없어도 해결되지 않은 메뉴 인식

저장소의 최근 기록에는 Blender의 열린 File 메뉴를 읽기 전용으로 평가한 사례가 있다. 실제 GUI 입력은 없고 실행 후보도 비어 있거나 `none` 하나였지만, 목표·조건·모드 확신이 게이트를 통과하지 못했다. 따라서 **후보 폭증은 유력한 원인 중 하나이지 모든 실패의 충분한 설명이 아니다.** [G9]

같은 보존 화면의 문맥에 실제 관측된 메뉴 항목이 들어가도록 바꾸면 조건 점수가 약 0.0363에서 0.1175로 변했지만 성공 판정에는 미달했다. 입력 해상도 관련 진단에서도 조건 점수가 0.1175→0.3471→0.5263으로 달라졌으나 해결되지는 않았다. 이 실험은 토큰 수·질문 위치도 함께 바꾸므로 시각 선명도 하나의 인과효과로 단정할 수 없다. [G9]

**진단 결론:** 후보 누락, 작은 UI의 정보 손실, 상태·조건의 표현, 모델의 영역 적합성, 판정 보정 문제가 얽혀 있다. 동일 입력에 대한 질문 문구 변경만 계속 반복하면 제품 작업은 진전되지 않는다.

## 3.2 d1은 이미 비교했으나 기본값은 유지 중

아래는 저장소의 CPU BF16 비교 기록이다. Ryzen 7 9700X급 호스트, 같은 준비 환경, 9개 저장 사례 중 7개 라벨 사례의 21개 필드 판단을 3회 반복했다. 서로 다른 GUI 작업 63개를 평가한 것은 아니다. [G3]

| 모델 | 기록된 필드 일치 | warm 중앙값 | peak worker RSS |
|---|---|---|---|
| CLEF-Flash | 63/63 | 19.858초 | 10.627GiB |
| d1-3B | 54/63 | 1.614초 | 6.656GiB |

d1은 이 기록에서 더 가볍고 빨랐지만 일부 progress 판단이 나빠졌다. Blender 사례는 정답 라벨이 없었고, OS 입력 없는 replay였다. **실시간 GUI 성공률이나 100ms 달성을 입증하지 못하므로 기본 모델 승격을 보류한 현재 판단은 타당하다.**

## 3.3 완료 상태를 세 축으로 분리

소프트웨어 릴리스, GUI 조작 성공, Reici의 시각적 품질은 별도 상태로 보고한다. 현재 진단 기록의 일부 Blender 씬은 여전히 빈 검사 상태이며, 런타임·패키징 검증이 자산 수정·리깅 완료를 의미하지 않는다. 다음 단계는 추가 진단 문서의 양이 아니라 **실제 실패 조작이 통과하는지**로 관리한다. [G9]

<!-- PAGEBREAK -->

# 4. ‘선택지 표준편차 0’의 올바른 진단

확률 벡터의 선택지 간 표준편차, 원시 logit의 분산, 같은 입력을 반복했을 때 출력의 분산은 서로 다른 양이다. 저장소의 ‘repeat dispersion 0’은 반복 결과가 같았다는 뜻이며, 선택지들이 같은 확률이라는 뜻이 아니다. 먼저 문제 로그가 무엇을 계산했는지 확인해야 한다. [G9]

확률 합이 1인 N개 선택지의 모집단 표준편차는 다음과 같다.

```text
sigma(p) = sqrt( sum_i (p_i - 1/N)^2 / N )
0 <= sigma(p) <= sqrt(N - 1) / N
```

N이 2 이상일 때 후보가 많아질수록 상한 자체가 감소한다. 따라서 서로 다른 후보 수에서 같은 절대 표준편차 임계값을 쓰면 안 된다. N=1이면 표준편차와 엔트로피는 0이지만, 잘못된 후보 하나를 남긴 상황에서도 선택 확률은 1이다. **분포의 집중도는 정답 존재나 실행 안전성의 증명이 아니다.**

### 필요한 진단 항목

| 질문 | 측정 및 대조 실험 |
|---|---|
| 정답이 후보에 있는가? | 독립 정답으로 coverage@K, 후보 절단 전후의 누락률 측정 |
| 후보 의미가 중복되는가? | 같은 연산을 가리키는 후보 묶음과 원래 ID를 함께 보존 |
| 관측이 충분한가? | 원본 전체 화면, 관심 영역, 확대 영역, 접근성 보조를 각각 비교 |
| 모델이 구별하지 못하는가? | 정규화 엔트로피 H/logN, 상위 두 확률 차이, 정답 순위, 부재 판정 |
| SDK/수치 문제인가? | 옵션 ID·mask·토큰 길이·dtype·raw/직렬화 값을 제한적으로 대조 |
| 문맥/순서에 과민한가? | 후보 순서 교환과 동치 문구를 오프라인에서 비교. 실제 클릭을 무작위화하지 않음 |

현재 코드에는 이미 정규화 엔트로피가 있다. 새로 추가할 것은 단일 지표가 아니라 **원인별 관측과 의사결정**이다. 모델별·업무별 reliability diagram, Brier score, risk-coverage 곡선을 held-out 데이터에서 평가하고 실제 입력 권한은 별도 guard가 관리한다. [G8]

### 하면 안 되는 해결

temperature를 낮춰 확률만 뾰족하게 만들기, 낮은 confidence gate로 억지 실행, 임의 top-K 절단 후 confidence 상승을 개선으로 보고하기, 동일 프레임 성공까지 반복하기는 배제한다. 불확실할 때는 더 유익한 관측·명령 검색·다른 제어 경로를 선택해야 한다.

<!-- PAGEBREAK -->

# 5. 공유한 MCJev에서 가져올 것과 가져오지 않을 것

X 게시물은 Hao AI Lab의 MCJev 프로젝트와 연결된다. 연구진의 글과 공개 저장소를 대조했다. 핵심은 **느린 전술 판단과 더 빠른 실행기의 분리**다. mineflayer가 게임 상태를 읽고 50ms tick에 반사 제어를 수행하며, 결정 모델은 작은 전술 집합을 고른다. [R1, R2]

| 관점 | MCJev의 공개 구성 | clef-use에 대한 의미 |
|---|---|---|
| 상태 | 게임 API 기반 사실을 간결한 텍스트로 구성 | 화면 전체를 매번 읽게 하지 말고 앱 상태를 먼저 구조화 |
| 행동 | 약 16개 선택지인 측정 workload, 전술별 실행 로직 | 픽셀·버튼의 나열 대신 검증된 조작 스킬 선택 |
| 제어 | tick 기반 actioner와 판단 head 분리 | held key, drag, 취소는 모델 응답을 기다리지 않게 하기 |
| 추론 | B200/GB200, 전용 CUDA graph fast path | resident·고정 shape·호출 경로 최적화의 근거 |
| 검증 | 실제 플레이 기록으로 하네스 수정 | 원래 Blender 실패를 패치 후 재실행하는 회귀 루프 |

### 24ms의 정확한 범위

연구의 모델은 DJev 방식으로 사용하는 DiffusionGemma 기반 결정기다. 공개 성능 문서는 B200의 약 26ms 요청-답변 경로와 GPU forward 약 22.8ms를 구분한다. 이것은 스크린샷 OCR·GUI grounding·OS 입력·앱 렌더링 전체를 포함한 데스크톱 시간은 아니다. [R2]

**따라서 ‘26B 모델이 24ms이므로 Blender도 된다’가 아니라, 어떤 일을 모델 밖으로 옮겼기에 그 시간이 가능했는지 배워야 한다.** 대형 GPU가 필요한 해당 모델을 사용자 PC의 기본 모델로 즉시 채택하는 안은 권하지 않는다.

### 추론 엔진에서 적용할 원칙

고정 입력 형상, resident worker, 지원되는 cache 재사용, 적은 직렬화, 작은 결과 텐서 반환을 우선한다. 배치는 처리량을 늘려도 큐 대기로 반응 시간이 늘 수 있다. 공개 실험에서도 여러 봇의 지연이 100ms를 넘는 조건이 있으므로 단일 desktop 반응 목표에 throughput 수치만 가져오지 않는다. 수치·cache 변경에 따른 선택 변화도 검증해야 한다. [R2]

이 프로젝트로부터 도출하는 설계는 **사실 중심 상태 → 작은 의미적 행동 공간 → 빠른 실행기 → 실제 결과 회귀**다. 화면 전체를 후보로 바꿔 결정기에 떠넘기는 현재 경로와는 중요한 차이가 있다.

<!-- PAGEBREAK -->

# 6. 복합 적용할 방법론과 채택 순서

| 방법 | 적용 위치 | 채택 판단 / 한계 |
|---|---|---|
| 상태 기계·재사용 스킬 | 계획과 반복 실행 사이 | 즉시 우선. ActionEngine의 앱 상태 메모리 관점을 GUI 스킬로 좁혀 도입 [R3] |
| 고속 actioner + 결정 head | 로컬 제어 루프 | 즉시 우선. MCJev의 역할 분리만 이전하고 게임 API 특권·GPU 수치를 섞지 않음 [R1, R2] |
| 학습된 좌표 비생성 grounding | 작은 아이콘·UI 영역 | GUI-Actor를 비교군/teacher로 사용. 실제 소형 head는 별도 학습·검증 [R4] |
| 이벤트 기반 준비·효과 검증 | 실행 전후 guard | 즉시 우선. Playwright의 구분을 참고하되 픽셀에 DOM 보장을 주장하지 않음 [R9] |
| 비동기 action chunk | brush·연속 drag | 제한 도입. RTC의 원리를 차용하되 로봇 실증을 GUI 실증으로 취급하지 않음 [R5] |
| 읽기 전용 사전 계산 | 다음 ROI·검색·분기 준비 | 후속 도입. 실제 데스크톱에 speculative write를 보내지 않음 [R6] |
| 행동-결과 학습 | 실패 복구와 마일스톤 판정 | VeriGUI의 실패·복구 데이터 관점을 도입. Android 결과와 Blender는 별도 [R7] |
| 단일 forward 다중 스케일 | grounding 추론 비용 | InnerZoom을 연구 추적 대상으로 유지. 검증된 공개 구현·가중치 확보 후 평가 [R8] |

### 우선순위 판단

바로 제품에 필요한 것은 더 많은 모델이 아니라, **올바른 상태와 행동 계약을 만드는 공학**이다. 새 backbone을 여러 개 상주시켜 모든 경로를 통과하게 하면 더 느리고 디버깅이 어려워질 수 있다.

ActionEngine은 앱을 상태·연산·전이로 기억해 재활용하고, GUI-Actor는 학습된 action head로 시각 영역을 찾는다. 두 방법은 경쟁 관계가 아니다. 전자는 ‘어떤 연산을 할 것인가’, 후자는 ‘그 연산의 대상은 어디인가’를 담당한다. [R3, R4]

### 지금 채택하지 않을 방향

처음부터 범용 VLA를 대규모 학습하는 안, 공개되지 않은 모델을 필수 의존성으로 삼는 안, 로컬 화면을 원격 대형 모델에 매 tick 전송하는 안, 모든 프로세스를 전면 재작성하는 안은 보류한다. 단기 실사용 개선과 관계없는 benchmark 점수 경쟁도 우선하지 않는다.

기존 Foundation ViT 경로는 버리지 않는다. 다만 검증된 특정 영역의 추적·재식별·grounding에 활용하고, ‘frozen feature가 있으므로 임의 지시를 정확히 수행한다’는 전제를 제거한다.

<!-- PAGEBREAK -->

# 7. 목표 아키텍처: State-Aware Reactive Skills

다음은 구현 제안이며 현재 완성된 기능을 표시한 그림이 아니다.

```text
Hermes / Codex / OMP
        |
    MCP / CLI                      느린 계획·품질 검토
        |                           LLM / Gemini
Goal + constraints + permissions ---------+
        |                                |
    Skill Compiler <----- repair / review+
        |
validated skill graph + typed parameters
        |
State Compiler <--- frames / app events / AX / DOM
        |              |                 |
        |         ROI observers     slow visual grounder
        |              |                 |
        +-------- current belief/state --+
        |
Reactive Skill Runtime
   | deterministic rule / cached skill
   | small decision model when ambiguous
   | bounded active perception when insufficient
        |
Input Transaction Scheduler + independent stop/watchdog
        |
keyboard + mouse + modifiers + local gesture controller
        |
OS / application ---> effect observer ---> skill state
```

### 시간축별 책임

**L0 입력·중단:** 현재 스킬에 허용된 key/button 소유권, 순서, 해제, 제스처 구간을 관리한다. 모델이 멈추어도 중단 가능해야 한다.

**L1 반응·관측:** 새 이벤트와 관심 영역 변화에 반응해 준비된 분기를 고른다. 새로운 해석이 필요할 때만 작은 결정기를 호출한다. 100ms 반응 예산의 주 대상이다.

**L2 의미 계획·grounding:** 처음 보는 UI나 모드, 큰 구조 변경, 어려운 target을 해석한다. 느린 경우를 숨기지 않고 deadline miss·fallback 비용으로 기록한다.

**L3 품질·학습:** Reici의 얼굴/헤어/표정 비교, 반복 실패 분석, 스킬·모델 개선을 맡는다. Gemini/AGY의 엄격한 검토는 여기에 배치한다.

‘에이전트가 직접 사용’한다는 것은 상위 LLM이 매 keyDown을 생성한다는 뜻이 아니다. 목표의 통제권을 유지하면서 검증된 저수준 제어를 로컬 런타임에 위임하는 구조다.

<!-- PAGEBREAK -->

# 8. State Compiler: 화면이 아니라 작업 상태를 전달

동일한 키와 좌표는 Blender의 편집기·모드·도구·선택 상태에 따라 다른 일을 한다. 목표와 스크린샷만 전달하는 대신, 다음 상태를 신뢰 수준과 함께 유지한다.

| 상태군 | 예시 | 알 수 없을 때 |
|---|---|---|
| 앱·환경 | 프로세스/창 ID, 버전, keymap, DPI, 화면 좌표 변환 | 일치하지 않는 스킬 cache 폐기 |
| 작업 문맥 | editor, Object/Edit/Sculpt 계열 mode, 활성 도구 | 작은 영역 재관측 또는 read-only 조회 |
| 입력 문맥 | text focus, IME composition, held modifiers, mouse buttons | 범용 단축키·문자 입력을 보류 |
| 대상 | 활성/선택 객체, 목표 영역, depth/occlusion 불확실성 | 안전한 시점 변경·검색·확인 절차 |
| 전이 | modal operator, popup, loading, redraw, pending action | 전이별 준비 조건으로 대기·취소 |
| 증거 | timestamp, frame ID, 출처, TTL, confidence, unknown | 오래된 증거로 새 입력을 허가하지 않음 |

각 필드는 `value / source / observed_at / validity / uncertainty`를 가진다. 모르는 것을 false로 바꾸거나, 이전 프레임의 상태를 영구 사실로 유지하지 않는다.

### 관측 수단의 역할 분담

원본 픽셀은 항상 보존 가능한 근거다. AX/DOM/UIA는 실제 앱이 내보내는 범위에서만 활용한다. Blender 읽기 전용 확장으로 모드·선택·활성 연산자를 관측할 수 있는 경로는 유용하지만, 이를 픽셀 전용 결과와 혼합하지 않는다. 앱 API로 모델을 수정하면 API-assisted 경로임을 별도로 기록한다.

### 모르는 것을 알아내는 행동

애매한 곳을 임의 클릭하기 전에 관련 패널 확대, 명령 검색, hover 후 tooltip 확인, 선택 상태 조회처럼 정보가 늘어나는 행동을 후보에 포함한다. 단, hover·zoom도 UI를 바꿀 수 있으므로 새 관측에서 다시 판정한다. 무제한 탐색 대신 정보 이득 예상치·지연·부작용을 비교한다.

### 왜 이 방법이 후보 분산 문제를 줄이는가

‘화면의 126개 요소 중 하나’에서 ‘현재 Transform modal에서 축을 제한할지, 값을 입력할지, 취소할지’로 조건이 바뀐다. **후보 수를 억지로 줄이는 것이 아니라 불가능한 연산을 상태에 따라 제외**하는 것이다. 누락된 정답은 별도 coverage 측정으로 드러나야 한다.

<!-- PAGEBREAK -->

# 9. 행동 단위를 버튼에서 스킬로 변경

스킬은 무조건 실행되는 녹화 매크로가 아니다. 목표, typed parameters, 사전조건, 단계별 guard, 효과, 실패 분기, 입력 예산을 가진 작은 상태 기계다.

```text
Skill: transform_selected(axis, amount, space)
requires: correct_editor, known_mode, selection_present,
          no_text_focus, known_keymap, no_conflicting_modal
steps: enter_transform -> await_modal -> constrain_axis
       -> enter_numeric_literal -> verify_preview -> commit
recovery: cancel_known_modal -> observe -> replan
forbids: shell, unrelated_window, unapproved destructive action
```

위 예시는 목표 계약이며 현재 지원 명령 문법은 아니다. 키 문자열은 런타임의 실제 keymap에서 해결한다.

### 계층화와 후보 생성

먼저 `navigate / select / transform / edit_property / inspect / recover` 같은 스킬군을 고르고, 관측된 문맥에서 적용 가능한 스킬만 retrieval한다. 다음으로 대상과 typed parameter를 채운다. 최종 실행 전에는 결합된 행동 전체가 유효한지 검증한다.

서로 독립적인 head로 `operation`, `target`, `key`를 각각 선택한 뒤 모순된 조합을 실행하면 안 된다. 요인분해는 검색 비용을 줄이는 수단이며, 최종 tuple 검증을 대체하지 않는다.

### 스킬 검색과 메모리

스킬 설명·적용 앱·모드·성공 전이를 인덱싱한다. cache key에는 앱 버전, keymap, 중요한 레이아웃·모드 조건이 포함된다. 성공한 trajectory를 곧바로 전역 스킬로 등록하지 않고, 다른 장면과 조건에서 검증한 뒤 승격한다.

스킬 저장소는 계층형 재사용 지식이지만 모든 사용자 화면을 저장하는 장기 기록장이 아니다. 개인정보·라이선스 제한 자산은 로컬에서 분리하고, 공개 가능한 스킬 정의와 사설 증거를 구분한다.

### 결정 모델의 새 역할

결정기는 이미 실행 가능한 소수 스킬 사이에서 판단하거나 불확실성·진행 상태를 요약한다. 하나의 후보밖에 없을 때는 확률 1을 의미 있는 검증 결과로 사용하지 않는다. 명확한 결정론적 분기는 모델 없이 실행하되, 기존보다 강한 문맥 guard와 감사 로그로 통제한다.

<!-- PAGEBREAK -->

# 10. 키보드·마우스 통합 입력 계약

현재 제품에는 텍스트 입력과 일부 키 기능이 있다. 문제는 일반 창 조작에 충분한 행동 언어가 아니라는 점이다. `press` 허용 키는 Escape/Enter/Tab/Backspace, `hotkey`는 Ctrl 또는 Command의 A/L 조합으로 제한되어 있고, 포인터 동작은 왼쪽 버튼 중심이다. [G4, G7]

### 제안하는 최소 Action IR

| 유형 | 필수 표현 |
|---|---|
| 키 | logical key, physical code 선택, down/up/tap, hold 기간, repeat 정책 |
| 동시 키 조합 | modifiers + 본키, 누름·해제 순서, target editor, 허용 문맥 |
| 문자 | exact literal, Unicode/IME/clipboard 경로, composition 상태, 제출과 분리 |
| 포인터 | 좌표계, 좌/우/가운데 버튼, wheel 수평·수직, 이동·누름·해제 |
| 복합 제스처 | modifier를 유지한 drag/orbit/pan, 경로 구간, 속도·시간 상한 |
| modal sequence | 시작 조건, 다음 상태 guard, preview, confirm/cancel |
| 제어 | deadline, cancel token, desktop lease, owned-input set, rollback class |

### 반드시 분리할 개념

문자 `A`를 입력하는 것과 단축키 A를 누르는 것은 다르다. 키보드 배열의 물리 위치, 표시 문자, 논리 키를 구분한다. 한글·일본어 입력기의 조합 중 상태는 일반 단축키와 충돌할 수 있다. 문자 전송 API가 문자열 전체를 보냈다는 사실도 앱이 올바르게 입력했다는 증거는 아니다.

앱의 keymap을 확인하지 않은 Ctrl/Command 자동 치환은 금지한다. 단축키의 대상은 전경 창뿐 아니라 해당 editor와 모드다. 입력 중 사람의 키/마우스 개입이나 창 변경이 감지되면 남은 예약 이벤트를 폐기한다.

### 입력 소유권과 안전한 종료

프로세스가 실제로 누른 키·버튼만 소유 집합으로 추적한다. 키 조합은 규정된 역순으로 해제하며, 오류·timeout·worker crash·foreground 변경 시 독립 watchdog가 해제한다. 여러 MCP client가 같은 desktop을 동시에 조작하지 않는다.

Windows의 SendInput도 이미 눌린 키 상태를 자동 초기화하지 않으며 권한 제한을 받는다. 낮은 수준의 API를 사용한다고 앱 문맥·기존 입력 상태·권한 검증이 사라지지 않는다. [R11]

<!-- PAGEBREAK -->

# 11. Blender용 첫 스킬과 실제 동작 예

명령 검색과 숫자 입력은 다수 아이콘을 찾는 문제를 크게 줄일 수 있다. 공식 기본 keymap의 F3 메뉴 검색, 변형 연산과 축 제한은 좋은 출발점이다. 아래 키 표기는 **기본 keymap 예시**이며 실제 설치 버전·설정을 확인해 매핑한다. [R12, R13]

## 예제 A: 선택한 객체를 X축으로 정확히 이동

```text
OBSERVE: viewport identity, mode, selection, no text focus
PREPARE: resolve active keymap; bind input lease
G                 -> wait for transform/modal witness
X                 -> verify intended axis/space
exact number      -> inspect numeric preview
Enter             -> verify committed transform
failure           -> Escape only if that modal is still active
```

숫자는 모르는 상태에서 임의 생성하지 않는다. 상위 목표의 정확한 값·단위·공간을 contract에 넣는다. object local/world 변환과 scene unit이 불명확하면 먼저 질의·관측한다. 한 번의 네트워크 명령 아래 실행할 수 있지만 내부 상태 전이는 관측으로 확인한다.

## 예제 B: 뷰포트 이동과 얼굴 수정

orbit/pan은 실제 keymap에서 가운데 버튼 및 보조 키 조합을 해결한다. 동작 전 대상 viewport와 문자 포커스 부재를 확인한다. 3D 시점이 바뀌면 이전 얼굴 좌표를 재사용하지 않고, 대상 영역을 다시 잡는다.

Grab/Smooth 등 편집 제스처는 ‘볼을 예쁘게’라는 포괄 목표를 그대로 실행하지 않는다. 상위 시각 모델이 기준 이미지와 현재 렌더를 비교해 작은 수정 영역·도구·상한을 제시한다. 로컬 컨트롤러는 짧은 구간으로 수행하고 실제 변화·취소 요청을 지속 관측한다.

### 첫 통과 대상 스킬 묶음

명령 검색 열기·실행, 편집기 전환, mode 전환, 객체 선택, 수치 transform, 속성 편집, outliner 검색, modifier가 있는 orbit/pan, bounded drag, brush 구간, modal 취소, 저장·내보내기 흐름을 선정한다.

Reici 작업에서는 얼굴 윤곽, 헤어 커브, 재질, 표정/웨이트 중 실제 수정 최소 네 종류를 이 경로로 검증한다. 단순 UI 클릭이나 Python 콘솔에 거대 모델 생성 스크립트를 넣는 것은 주 GUI 제작 증거가 아니다. Blender API는 보조 및 별도 oracle로 구분한다.

<!-- PAGEBREAK -->

# 12. 관측을 직렬 파이프라인에서 이벤트 흐름으로

현재는 전체 화면 캐시가 깨지면 OmniParser를 거친 뒤 라우팅한다. 새로운 설계에서는 어떤 관측이 필요한지 먼저 판단한다. 단순히 별도 thread를 늘리는 것이 아니라 **불필요한 작업을 실행하지 않는 것**이 목적이다. [G6, G7]

### 제안하는 관측 경로

새 창·큰 레이아웃 변경에는 전체 파싱과 semantic grounding을 사용한다. 같은 작업 구간에서는 focus, modal, 선택 상태, active region 변화 등 작은 observer를 사용한다. 고해상도 crop, 짧은 텍스트, 접근성 이벤트, 검증된 target tracking을 조합한다. 앱이 정보 제공을 지원하지 않는 경우에는 픽셀 기반 관측으로 정확도를 측정한다.

로컬 이미지 전달은 공유 메모리나 소유권이 명확한 frame buffer 참조를 사용한다. 같은 화면을 start/end/path query마다 PNG로 재인코딩하지 않는다. batch query가 정확도·지연에 이득인지 측정하고 필요 시 target만 묶는다.

### 캐시가 보존할 것과 보존하지 않을 것

저장 가능한 것은 이미지 feature, 관측된 사실, 검증된 스킬 구조다. **과거 클릭 좌표의 실행 허가, 과거 안전 판단, 완료 판정을 cache hit라는 이유로 재사용하지 않는다.** 새로운 행동에는 유효한 관측과 문맥이 필요하다.

Evidence lease는 창/editor ID, 해당 대상의 기하, 핵심 주변 영역, semantic state version, timestamp/TTL에 묶는다. 다른 영역의 caret가 깜빡였다고 모든 정보를 버리지는 않되, target 이동·가림·modal 전환은 즉시 무효화한다. 기존 strict hash 경로는 기준 비교와 fallback으로 보존한다.

### 동적 화면에서의 검증

전체 화면 정지를 요구하면 애니메이션·뷰포트 렌더·게임에서 영원히 기다릴 수 있다. ‘이번 스킬에 필요한 조건이 준비됐는가’로 바꾼다. 고정된 컨트롤은 stability, 연속 드래그는 추적 일관성과 오차, 텍스트 입력은 값과 composition, 모드 전환은 mode witness를 확인한다.

이벤트가 도착했다는 사실만으로 성공 처리하지 않는다. 이벤트 유실·순서 뒤바뀜·오래된 프레임을 검출하고, 모델·observer 판단이 충돌하면 제한된 재관측을 수행한다.

<!-- PAGEBREAK -->

# 13. 100ms의 측정 정의와 반응 예산

**목표는 올바른 다음 행동이 빨리 나오는 것이다.** API 접수 확인, 캐시된 status 반환, 오류로 빠르게 종료한 시간을 성능으로 계산하지 않는다.

```text
reaction_ms = first_relevant_OS_event_time - real_state_change_time
observation_age_ms = input_commit_time - observation_time
policy_ms = policy_result_time - policy_request_time
completion_ms = verified_goal_time - user_goal_time
```

실험용 앱에서는 실제 상태 변경 timestamp를 oracle로 기록한다. 일반 앱에서 정확히 모르면 화면 샘플링 오차를 명시하고 관측 가능 시점 기준 측정도 함께 제공한다. 원격 호스트는 clock offset·network를 따로 계측한다.

### 목표 예산: warm 로컬 빠른 경로, 미검증 제안값

| 단계 | 초기 예산 |
|---|---|
| 변화 감지·프레임 확보·로컬 전달 | 12ms |
| 상태 갱신·필요 ROI 처리 | 18ms |
| 스킬 선택 / 경량 정책 | 25ms |
| 권한·문맥 guard | 5ms |
| OS 입력 전달 | 5ms |
| OS/GPU 경합·스케줄링 여유 | 20ms |
| 미배정 headroom | 15ms |
| 합계 | 100ms |

이 예산은 측정 결과가 아니다. 모델·Blender의 GPU 공유, 화면 크기, 실제 지원 장치에서 프로파일해야 한다. 각 단계 p95를 더하는 것은 전체 p95의 통계적 추정이 아니므로 end-to-end timestamp가 최종 기준이다.

### 발표·검증 규칙

모든 지원 작업에서 100ms를 deadline으로 기록하고 p50/p95/p99, 최댓값, deadline miss 비율을 함께 제시한다. 첫 릴리스 gate는 지원된 warm 경로의 p95 ≤100ms로 제안하지만, 이것을 ‘모든 호출의 절대 상한’으로 광고하지 않는다. Cold load·새로운 layout·복잡한 재계획은 별도 보고하되 전체 지연 분포에서 숨기지 않는다.

앱이 렌더링·로드하는 시간과 길게 지속되는 brush의 총 실행 시간은 반응 시간과 다르다. 지속 동작 중 중단·새 관측에 반응하는 시간도 따로 측정한다. 일반 데스크톱 OS에서 절대 hard-real-time 보장은 별도 검증 없이 주장하지 않는다.

<!-- PAGEBREAK -->

# 14. 스케줄러와 모델 서빙 최적화

### 불필요한 직렬 구간 제거

MCP는 외부 control plane으로 유지하고 각 key/button 이벤트가 하네스를 왕복하지 않게 한다. 입력 취소·해제는 모델 worker와 다른 실행 경로를 갖는다. 연속 frame은 latest-wins로 교체하고 오래된 inference 결과는 state version을 확인한 뒤 폐기한다.

의미 분석이 필요한 새 상태는 느린 경로로 보내되, 이미 승인된 스킬의 로컬 guard·중단 기능을 막지 않는다. 단, 앞선 해석이 실패한 상태에서 임의의 다음 행동을 계속하는 것은 금지한다.

### 모델 호출 자체를 작게 만든다

전체 화면·여러 질문·긴 history를 매번 처리하는 대신 현재 스킬의 선택 문제와 필요한 근거만 전달한다. 목표 완료와 엄격한 품질 검토는 마일스톤으로 분리한다. 반복되는 프롬프트 앞부분은 고정하되, KV/feature cache는 모델의 인과·attention 구조와 SDK가 허용할 때만 재사용한다.

공식 d1 수치는 RTX 4090 BF16 warm 조건에서 짧은 단일 질문 8ms, 384px 이미지 17ms지만 3.4k-token 상태는 102ms다. 같은 모델도 입력 구성에 따라 전체 반응 예산을 넘는다. 장치·질문 수·compile 조건이 다른 수치를 제품 보장으로 사용하지 않는다. [R14]

### 최적화 실험 순서

먼저 capture, 전처리, tokens, queue, forward, GPU 동기화, input, wait를 분리 측정한다. 이후 resident warmup, 지원 shape bucket, 공식 compile/CUDA graph, 필요한 head 출력만 반환, 로컬 frame 공유를 순서대로 비교한다.

양자화·kernel·cache 변경은 확률과 선택을 바꿀 수 있다. 수치 차이뿐 아니라 실제 오류·거부·완료 위험과 latency를 함께 비교한다. MCJev의 kernel 구성과 cache를 CLEF/d1의 다른 아키텍처에 그대로 이식하지 않는다. [R2]

### 자원과 다중 클라이언트

추론기는 background 재질 렌더 등과 자원을 공유하므로 메모리 admission과 예약을 적용한다. 모델 가중치 크기만으로 동시 실행 가능성을 판단하지 않는다. batch 대기창은 deadline 잔여 예산 안에서만 허용한다. 처리량을 올리기 위해 단일 사용자의 반응을 희생하지 않는다.

<!-- PAGEBREAK -->

# 15. Grounding·결정 모델의 역할과 학습 계획

## 15.1 모델 역할을 분리한다

| 역할 | 우선 후보 | 기본값 승격 조건 |
|---|---|---|
| 스킬·작은 상태 결정 | d1-3B와 기존 CLEF 비교 | 동일 live task 성공·오입력·지연·memory의 공동 개선 |
| 처음 보는 GUI target 찾기 | GUI 학습을 거친 grounder/GUI-Actor 계열 비교 | 작은 아이콘·중복 라벨·새 DPI의 held-out 결과 |
| 알려진 target 추적 | 가벼운 ROI·feature·기하 observer | 이동·가림·시점 변화 시 무효화 정확도 |
| 모드·포커스 판정 | 구조화 신호 우선, 작은 classifier 보조 | unknown/충돌을 분리하고 오진입 위험을 검증 |
| 제작 품질 검토 | Gemini/상위 시각 모델 | 실제 기준 이미지·동일 시점 렌더의 독립 검토 |

GUI-Actor는 action token과 시각 patch 정렬을 학습하는 접근이다. 현재의 frozen SigLIP patch 유사도와 같은 보장을 주는 모델이 아니다. 학습된 head와 target-absent·ambiguity 데이터를 우선 검토한다. [G10, R4]

## 15.2 초기 데이터 수집

실제 실패 및 성공에서 screenshot/ROI, goal, app/editor/mode/keymap, target, 허용 행동, 결과, 지연을 수집한다. 오류를 `target missing`, `wrong mode`, `stale`, `wrong key`, `effect absent`, `false completion`처럼 분류한다.

대규모 학습 전에 수백 개의 독립 문제에서 구조 변경을 평가한다. 필요한 범위가 확인된 뒤 수천 개 이상의 정답·부재·방해 대상 예시를 모아 작은 head/adapter를 학습하는 실험을 계획한다. 수량은 성공 보장이 아니라 수집 예산이며, 성능 포화 여부로 확장한다.

## 15.3 데이터 누수·편향 방지

train/validation/test는 프레임 단위가 아니라 장면·작업·layout·세션 단위로 분리한다. 동일 스크린샷의 crop나 증강본이 test로 새어 들어가면 안 된다. 여러 정답 좌표가 있는 UI는 허용 영역으로 라벨링한다. 부재·가림·동일 텍스트 복수 대상도 포함한다.

teacher의 confidence나 설명을 정답으로 삼지 않는다. 필요한 경우 read-only 앱 상태, 실제 결과, 사람의 수정으로 독립 라벨을 만든다. Gemini의 얼굴 검토 PASS는 키 입력 안전성 증거가 아니다. d1을 도입하더라도 기존 grounder와의 feature 공유는 별도 호환성 실험 후 진행한다.

<!-- PAGEBREAK -->

# 16. 검증·안전·자율성의 재배치

빠르게 만들기 위해 안전 검사를 없애지 않는다. **싼 필수 guard는 매 이벤트, 비싼 의미 검사는 적절한 경계**에 배치한다.

| 단계 | 검사 | 실패 처리 |
|---|---|---|
| 매 입력 | lease, cancel, 창/editor, 모드 충돌, held input, deadline | 즉시 미전달·해제 |
| 상태 전이 | target 존재, modal/포커스, 값·선택·축 witness | 재관측·검증된 취소 |
| 스킬 종료 | 기대 효과, 범위·오차, 변경 저장 여부 | 실패 분류·복구·상위 재계획 |
| 작업 종료 | 모든 목표 조건, 독립 readback·fresh evidence | 완료 보류 |
| 제작 품질 | 기준과 실제 결과의 시각 비교·deformation | 수정 단계로 회귀 |

VeriGUI는 이전 행동의 결과를 검증하고 실패·복구 데이터를 학습하는 방향을 제시한다. 이 원리를 채택하되 현재 code의 조건 검증을 단순 확률 임계값 완화로 대체하지 않는다. [R7]

### 위험도별 정책

일반 viewport 이동과 되돌릴 수 있는 작은 편집은 scope가 제한된 스킬로 허용한다. 파일 삭제, 외부 전송, 로그인 정보, 구매·게시, 콘솔 명령 등은 별도 권한과 확인을 요구한다. ‘숫자 입력’과 ‘임의 명령 문자열 실행’은 같은 capability가 아니다.

화면의 텍스트·툴팁·문서는 관측 근거이지 새로운 지시나 승인으로 해석하지 않는다. 자동 shortcut 검색 결과 역시 실제 목표·권한과 일치하는지 확인한다.

### 사전 계산과 action chunk의 한계

Speculative Actions를 참고한 병렬화는 우선 다음 crop·feature·후보·스킬 분기의 준비에 한정한다. 실제 사용자 화면에서 확인 전 클릭을 실행한 뒤 Undo로 없던 일로 만드는 설계는 채택하지 않는다. [R6]

RTC에서 차용한 비동기 구간 제어는 제안된 연구 방향이다. 실행이 확정된 짧은 구간과 수정 가능한 미래 구간을 나누되, GUI modal 전이·보조 키 해제·사용자 중단 조건을 우선한다. 로봇 환경에서의 성능을 Blender 결과로 광고하지 않는다. [R5]

<!-- PAGEBREAK -->

# 17. 평가 체계: 정확도와 100ms를 함께 검증

단순 성공한 응답만 모은 latency는 실패를 숨긴다. 제품 목표는 **시간 안에 올바른 작업을 진행시키는 비율**이다.

```text
goodput_100 = correct, useful actions within 100ms
              / predefined action opportunities
fast_coverage = opportunities supported by fast path
                / all opportunities in the declared suite
```

correct/useful은 독립 oracle로 평가한다. WAIT/ABORT는 안전성에 필요하지만, 전진 행동과 별도 집계해 아무것도 하지 않는 제품이 높은 점수를 얻지 못하게 한다. 지원 범위를 실행 후 유리하게 재정의하지 않는다.

### 평가 데이터와 단계

| 단계 | 최소 권고 범위 | 핵심 판정 |
|---|---|---|
| 진단 | 기존 실제 실패, 부재·중복·단일 후보 통제 사례 | 평탄화·정보 손실·문맥·입력 문제 분리 |
| 단일 스킬 | 10–12개 Blender 핵심 스킬, 변형 layout/keymap | 실제 실행·독립 readback, 키·버튼 누수 0 |
| 반응 스트레스 | 사전 정의 1,000회 이상 변화/입력 기회 | p50/p95/p99, miss, useful goodput, queue age |
| 통합 작업 | Blender + 브라우저 + 편집기, 장면·언어·DPI 변화 | task success, 총 시간, 개입·복구·오완료 |
| Reici 제작 | 얼굴·헤어·재질·표정/웨이트의 실제 수정 | GUI 참여 증거와 Gemini 독립 품질 gate |

1,000회는 충분한 통계 보장을 뜻하지 않는다. 독립 시행에서 오류 0회라도 95% 상한은 대략 3/n이며, 동일 세션의 상관된 이벤트는 더 신중하게 해석한다. 신뢰 구간은 세션·작업 단위로 계산한다.

### 반드시 분리 보고할 접근 수준

`PIXELS_ONLY`, `ACCESSIBILITY_ASSISTED`, `APP_TELEMETRY_ASSISTED`, `API_ASSISTED`를 구분한다. 평가 oracle이 이용하는 특권 정보가 agent 입력에 몰래 들어가면 안 된다. 순수 화면 인식 모델과 API 상태를 읽는 스킬 실행기를 같은 조건이라고 주장하지 않는다.

OSWorld-Human의 관점처럼 task 성공뿐 아니라 불필요한 동작·계획·추론 비용도 측정한다. 모델 benchmark와 실제 GUI E2E를 별도 표로 유지한다. [R15]

<!-- PAGEBREAK -->

# 18. 비교 실험과 릴리스 통과 기준

### 단계적 ablation

| 변형 | 변경 내용 | 답해야 하는 질문 |
|---|---|---|
| A0 | 고정한 현재 릴리스 | 현재 제품의 실제 실패·지연은 무엇인가? |
| A1 | 결정 모델만 교체 | d1의 영향과 데이터·프롬프트 영향이 분리되는가? |
| A2 | 입력 IR·키보드 스킬 | 후보 나열 대신 연산 단위 제어가 개선하는가? |
| A3 | 이벤트·ROI·스킬 cache | 전체 파서와 모델 호출이 실제로 줄었는가? |
| A4 | 학습된 grounding | 후보 부재·tiny target·새 layout에서 좋아지는가? |
| A5 | compile·공유 프레임·스케줄러 | 품질 유지 하에 잔여 hot path가 줄었는가? |

매 비교는 동일 장면 복원과 동일 task seed에서 수행하고 실행 순서를 교차한다. 시도 횟수, cold/warm, 실패·거부, precision, tokens, 해상도, GPU 점유를 보존한다. 원래 실패의 패치 검증과 아직 보지 않은 장면의 일반화 검증은 별도다.

### 제안하는 첫 출하 gate

**기능:** 키보드·좌/우/가운데 버튼·modifier gesture·known-modal cancel이 통합 스킬에서 동작하고, 사람 개입·창 이동·worker crash에 입력을 해제한다.

**정확도:** 사전 정의 suite에서 현재 baseline 이상이며, 평탄화/문맥/키보드 누락으로 실패했던 작업을 개선한다. p95만 좋아지고 성공률이 떨어지면 출하하지 않는다. 중요한 오완료·허용 범위 밖 입력은 개별 blocker로 취급한다.

**속도:** 선언한 warm 빠른 경로에서 p95 ≤100ms를 통과하고, 전체 suite의 fast coverage와 goodput을 함께 발표한다. 초기 coverage 목표는 80%로 제안하되 실제 작업 혼합에 맞춰 사전 고정한다. 새로운 상태의 느린 fallback도 전체 지연·coverage에 반영한다.

**제품:** 설치된 릴리스로 실제 조작을 다시 수행한다. 개발 checkout만 성공하면 미완료다.

### 추적용 telemetry

`trace_id, task_id, app_profile, skill_id, state_version, frame_time, model_revision, input_tokens, candidate_coverage, entropy, margin, queue_ms, perception_ms, policy_ms, first_input_time, effect_time, outcome, abort_reason`을 기록한다. 원시 화면·문자열·모델 내부 텐서는 기본 비공개·최소 보관으로 둔다.

<!-- PAGEBREAK -->

# 19. 구현 백로그와 코드 변경 지점

전면 V3 재작성보다 feature flag 아래 얇은 수직 구현을 추천한다. 아래 신규 이름은 제안이며 존재하는 API로 오해하지 않는다.

| 우선순위 | 작업 | 기존 연결 지점 | 완료 증거 |
|---|---|---|---|
| P0 | 실제 실패 taxonomy·확률/지연 계측 | decision 계약, benchmark, `_choose` | 후보 부재·반복 분산·평탄 분포를 구별한 재현 보고 |
| P0 | 키보드/버튼/보조키 Action IR | `schema.py`, `DesktopAction`, WindowsInput | modifier drag·MMB·numeric sequence·취소의 native E2E |
| P1 | 상태 컴파일러 + 스킬 FSM | `router.py`, `candidates.py`, runtime | 실제 mode/keymap에 맞는 첫 5개 스킬 |
| P1 | 독립 watchdog·입력 스케줄러 | desktop lease·abort·release | 모델 정지 중에도 release 통과 |
| P1 | cheap observation 우선 라우팅 | `_parse`, capture, VisualWaiter | 전체 파서 호출 감소와 최신 상태 일치 |
| P2 | frame 참조·병렬 read-only 준비 | JsonWorker·encode_image·grounder | 동일 화면 재인코딩 감소, stale action 0 |
| P2 | d1/CLEF·학습 grounder 비교 | 기존 DecisionBackend·VisualWorker | held-out task와 동일 조건의 비교 |
| P3 | serving 최적화·data flywheel | model worker·ML profile | 품질 비열화 없는 latency 개선 |

### 범위 통제

현재 코어의 강점을 재사용한다. 기존 `old/`를 다시 변경하지 않는다. 새 state/skill 모듈은 실제 첫 조작을 구현할 만큼만 만들고, 모든 프로그램의 추상 GUI 모델을 먼저 설계하지 않는다.

`JsonWorker`의 숨겨진 stderr는 개인정보를 제거한 제한적 진단 로그로 보완한다. 전체 문서·원시 tensor를 무제한 쌓지 말고, 재현에 필요한 최소 경계 정보와 source/hash를 보존한다. [G7]

### 첫 기술 목표

‘Blender File 메뉴가 열렸는가’를 읽기 전용 oracle와 픽셀 경로로 각각 검증하고, ‘선택된 객체의 수치 이동’을 통합 입력 스킬로 수행한다. 이 두 동작에서 상태 인식, 올바른 분기, 키보드 연산, 실제 결과 검증이 연결되면 다음 스킬을 확장한다.

<!-- PAGEBREAK -->

# 20. 실행 일정·배포·운영 제안

다음 일정은 전담 runtime/입력 개발 1명, 모델·평가 개발 1명과 리뷰 역할을 가정한 계획 추정이다. 단독 작업·데이터 부족·드라이버 문제는 기간을 늘릴 수 있다. 달력보다 통과 증거를 우선한다.

| 단계 | 예상 구간 | 산출물 및 다음 단계 조건 |
|---|---|---|
| 진단·기반 | 1주차 | pinned baseline, failure corpus, 실제 입력 지연, 독립 abort 검증 |
| 행동 공간 | 2주차 | 통합 IR, keymap-aware input, 5개 핵심 스킬, 실제 재현 통과 |
| 빠른 실행 | 3–4주차 | 이벤트·상태·ROI, 나머지 스킬, 100ms budget 프로파일 |
| 품질·모델 | 5–6주차 | grounder/decision 비교, held-out accuracy·goodput 보고 |
| 실사용 출하 | 7–8주차 | Reici dogfood, 지원 플랫폼 canary, 설치·업데이트 검증 |

### 플랫폼 범위

첫 저지연 프로파일은 실제 사용 머신의 GPU·메모리·앱 동시 점유를 측정한 뒤 고정한다. CPU fallback을 제공하더라도 100ms 제품 등급과 동일하게 표시하지 않는다. Windows/macOS/Linux의 입력 권한·IME·캡처 지원은 각각 시험한다. Wayland나 특정 앱의 정보 접근 제한도 숨기지 않는다.

### 배포 계약 유지

공통 MCP/CLI와 Codex/Hermes/OMP 통합은 유지한다. 스킬 실행은 기존 고수준 작업 계약의 확장으로 노출하고, 필요하지 않은 수십 개 low-level tool을 하네스에 추가하지 않는다. capability/version negotiation과 기존 contract migration을 제공한다.

`install.sh`, `install.ps1`, 공통 manifest·체크섬, 원자적 전환·복구, 모델 cache 보존, 네 언어 설정 문서를 유지한다. 새로운 입력 권한과 스킬 profile을 `doctor`에서 명확히 보여 준다. 동일 source/revision이 설치된 제품에서 실제 조작을 재현해야 한다.

### 출하 단계

오프라인 replay → 격리된 실제 GUI → 소수 사용자 canary → 정식 릴리스로 이동한다. 실패가 늘면 feature flag로 스킬 경로를 끄고 기존 V2로 돌아갈 수 있어야 한다. avatar/참고 이미지/제한된 BOOTH 파츠는 코드 릴리스에 포함하지 않는다.

이번 제출은 기획서다. 코드 수정·커밋·업로드·공개 배포는 수행하지 않았다.

<!-- PAGEBREAK -->

# 21. 최종 결정과 연구 리스크

## 채택 권고

**제품의 중심을 Decision Model 호출에서 상태 기반 스킬 실행으로 옮긴다.** CLEF/d1/grounder는 목적별 플러그인이고, 공통 핵심은 신뢰 가능한 관측, 통합 입력 계약, 검증된 스킬, deadline-aware 실행, 결과 증거다.

키보드 지원은 마우스 API 옆에 `press()`를 추가하는 작은 기능이 아니다. 작업의 표현 자체를 `button_42`에서 `transform(axis=X, amount=...)`로 바꾸는 핵심 수단이다. 현재 코드가 지원하지 않는 입력은 모델의 지능으로 보충되지 않는다.

## 남는 연구 문제

**정보가 없는 화면:** 픽셀만으로 selection/mode/3D depth를 구분할 수 없는 경우가 있다. 능동 관측과 사용 가능한 구조화 신호를 더하고, 그래도 모르면 안전하게 거부한다. 해당 상태는 아직 제품 지원 범위 밖임을 수치로 드러낸다.

**새로운 작업의 100ms:** 준비된 스킬이 없는 완전히 새로운 작업을 처음부터 해석하는 시간까지 모든 하드웨어에서 100ms라고 주장할 근거는 없다. 빠른 경로의 적용률을 넓히는 것이 연구 목표이며, 처음 보는 상황의 지연을 숨기는 것은 해법이 아니다.

**재사용과 과적합:** 스킬이 특정 창 좌표에 고정되면 기존 문제를 이름만 바꾼다. 앱 버전·keymap·layout 변화에서 재검증하고 상태 guard와 target 재획득을 필수로 한다.

**모델 확신과 안전:** 높은 확률, 낮은 엔트로피, Gemini PASS는 승인이나 실제 결과의 대체재가 아니다. 검증 실패를 숨기지 않고 필요한 관측과 결과 조건을 개선한다.

## 조사 한계

MCJev는 X 단문만으로 해석하지 않고 연구진 글과 공개 구현을 대조했다. 일부 Blender 최신 매뉴얼 본문은 접근 오류가 있어 공식 검색 노출 내용과 확인 가능한 자료의 범위에서만 설명했다. 특정 사전 컴파일 정책 트리 논문은 원문 접근이 확인되지 않아 필수 기술 근거로 채택하지 않았다. InnerZoom의 논문상 공개 예정 표현도 제품 의존성으로 간주하지 않았다.

**성공의 마지막 기준:** 기존에 무너졌던 프로그램을 더 적은 해석 호출과 더 풍부한 실제 입력으로 정확히 조작하고, 그 성능을 설치된 제품에서 재현하는 것이다. 더 빠른 softmax만으로는 이 기준을 만족하지 못한다.

<!-- PAGEBREAK -->

# 부록 A. 소스 감사 인덱스

모든 제품 파일은 아래 고정 커밋 기준이다. 문서의 [G] 표시는 이 목록을 참조한다. 원시 로그·비공개 화면은 저장소 문서에 기록된 범위까지만 확인했다.

```text
repository: snowman0919/clef-use
commit: 4c725eec736d30eda979298143cd90a61f8a22ee
base URL:
https://github.com/snowman0919/clef-use/blob/
4c725eec736d30eda979298143cd90a61f8a22ee/
```

| ID | 파일 / 리소스 | 검토한 근거 |
|---|---|---|
| G1 | GitHub `branches/main` 및 commit metadata | 검토 시점 SHA·UTC 시각 |
| G2 | GitHub `releases/latest` | v0.1.28 게시·아티팩트 정보 |
| G3 | `docs/DECISION_MODELS.md` | 공통 backend, d1 실제 구현, CPU replay, 승격 보류 |
| G4 | `src/clef_use/candidates.py` | 후보 정렬·절단·keyboard 생성 제한 |
| G5 | `src/clef_use/router.py` | mode 라우팅, semantic subset, visual query loop |
| G6 | `src/clef_use/runtime.py` | `_parse`, `_choose`, `execute`, pre-input·completion 경로 |
| G7 | `src/clef_use/backends.py` | JsonWorker, encoding, capture, DesktopAction, factory |
| G8 | `src/clef_use/backends.py::DecisionBackend` | normalized entropy 및 named answer 해석 |
| G9 | `docs/V2STATUS.md` | File ASSESS, 전처리·문맥·candidate 진단 및 한계 |
| G10 | `docs/HYBRID_EXECUTION.md` | SigLIP readout, 선택적 head, 학습·confidence 한계 |
| G11 | `src/clef_use/verification.py`, `config.py` | 50ms polling·stable samples·ROI·default |
| G12 | `docs/VISUAL_READINESS.md` | readiness 범위·실제 Windows 기록·future limitations |

원문 탐색 시 디렉터리명·함수명을 그대로 검색하면 된다. G6은 실행 루프의 관련 구간을, G7은 모델 요청·capture/input·factory 구간을 중심으로 검토했다. 전체 저장소의 모든 행을 감사했다는 의미는 아니다.

출시 전에는 이 커밋의 결론을 새로운 HEAD에 그대로 적용하지 말고 diff를 확인한다. 어떤 개선이 이미 반영되었으면 중복 구현하지 않는다.

<!-- PAGEBREAK -->

# 부록 B. 1차 연구·공식 자료

아래 URL은 실제 조회한 1차 자료다. 연구의 입력 특권·하드웨어·분야를 확인한 뒤 적용한다. [R1–R9]는 방법론 근거, [R10–R15]는 API·모델·평가 근거다.

**[R1] Hao AI Lab — MCJev 연구 글.** 게임 상태를 구성하는 harness, tactical head와 fast actioner의 구분. 24ms가 시각 데스크톱 전체 지연이 아니라는 해석의 근거.
https://haoailab.com/blogs/mcjev/

**[R2] MCJev 공개 구현 및 성능 노트.** decision workload, B200/GB200, CUDA graph, prefix cache, queue/batching, 수치 일관성 한계.
https://github.com/hao-ai-lab/MCJev
https://github.com/hao-ai-lab/MCJev/blob/main/serving/docs/PERFORMANCE.md

**[R3] ActionEngine, arXiv:2602.20502, v2.** 재사용 가능한 앱 상태 기계 메모리와 programmatic execution. 웹 실증이며 Blender에 자동으로 같은 성능이 나오지 않는다.
https://arxiv.org/abs/2602.20502

**[R4] GUI-Actor, arXiv:2506.03143.** 학습된 attention action head와 coordinate-free target grounding.
https://arxiv.org/abs/2506.03143
https://github.com/microsoft/GUI-Actor

**[R5] Real-Time Execution of Action Chunking Flow Policies, arXiv:2506.07339.** 비동기 구간 실행. 로봇 분야의 결과를 GUI 적용 가설로 구분.
https://arxiv.org/abs/2506.07339

**[R6] Speculative Actions, arXiv:2510.04371, v2.** 다음 행동을 준비하는 병렬화. 실제 GUI의 irreversible side effect에는 그대로 적용하지 않음.
https://arxiv.org/abs/2510.04371

**[R7] VeriGUI, ACL 2026.** 행동 결과·실패 인식·복구를 학습하는 TVAE 및 robust training 관점.
https://aclanthology.org/2026.acl-long.1335/

**[R8] InnerZoom, arXiv:2606.30084.** 다중 스케일 evidence를 하나의 forward에서 활용하는 연구. 논문에 code/model 공개 예정으로 기재되어 있으므로 채택 전 가용성 확인 필요.
https://arxiv.org/abs/2606.30084

<!-- PAGEBREAK -->

# 부록 B. 1차 연구·공식 자료 — 계속

**[R9] Playwright — Auto-waiting.** visible/stable/enabled/editable 등의 구분. DOM 기반 보장을 픽셀 observer에 그대로 주장하지 않는다.
https://playwright.dev/docs/actionability

**[R10] PyAutoGUI — Fail-Safes.** 기본 `PAUSE=0.1`, macOS catch-up 지연, 긴급 정지의 필요성.
https://pyautogui.readthedocs.io/en/latest/index.html

**[R11] Microsoft — SendInput.** 입력 이벤트 전달, 기존 keyboard state, UIPI 제한.
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput

**[R12] Blender — Default Keymap / Operators.** 기본 F3 Menu Search의 공식 검색 노출 자료. 최신 본문은 조회 시 접근 오류가 있어 전체 본문을 읽었다고 주장하지 않음.
https://docs.blender.org/manual/en/latest/interface/keymap/blender_default.html
https://docs.blender.org/manual/en/latest/interface/operators.html

**[R13] Blender — Axis Locking / Numeric Input.** 변형 연산의 축 제한·숫자 입력. 실제 실행은 설치된 keymap·버전·unit을 먼저 확인.
https://docs.blender.org/manual/en/latest/scene_layout/object/editing/transform/control/axis_locking.html
https://docs.blender.org/manual/en/3.3/scene_layout/object/editing/transform/control/numeric_input.html

**[R14] Liquid AI — d1-3B 모델 카드.** typed decision API, 입력 크기에 따른 warm latency, compile 조건. 모델·원격 코드 license는 앱 license와 분리.
https://huggingface.co/LiquidAI/d1-3B

**[R15] OSWorld-Human, arXiv:2506.16042.** computer-use의 성공률과 실행 효율을 함께 평가하는 관점.
https://arxiv.org/abs/2506.16042

### 숫자를 인용할 때 유지할 경계

모델의 짧은 입력 지연, 저장된 화면 replay, 실제 OS 입력, 앱 효과 확인, 최종 작업 성공은 서로 다른 계층이다. 비교 표에는 hardware, model revision, precision, input size, warm/cold, sample count, 포함한 시간을 반드시 명시한다.

‘빠른 모델 + 좋은 파서 + 여러 guard’의 개별 성능을 더하거나 평균해 제품 성능을 만들어내지 않는다. 최종 근거는 전체 경로의 timestamp, independent outcome, 모든 실패 시도의 기록이다.

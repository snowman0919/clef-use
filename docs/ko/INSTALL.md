# 설치

0.1.51부터 가이드/MCP 자동 갱신은 업데이트하는 설치본에 연결된 등록에만 적용됩니다.
별도 root/bin에 새로 설치해도 다른 설치본의 승인된 프로필을 가져오지 않습니다.
사용자가 수정했거나 다른 root에 속한 launcher는 보존하고 거절하므로 별도
`CLEF_USE_BIN_DIR`을 지정하세요. 등록 잠금 안에서 소유권을 다시 확인합니다.
이 launcher 보호에는 새 설치 프로그램이 필요합니다. 이미 내려받은 0.1.50
bootstrap이 새 CLI 실행 전에 공용 launcher를 덮어쓰는 동작까지 고칠 수는 없습니다.
구버전 CLI로 자기 설치본을 업데이트하면 새 CLI의 등록 소유권 검사가 적용됩니다.
수동 이동은 `integrations refresh --managed-only --command-path`에
`--previous-command`를 명시할 수 있습니다.
[실제 패키지 검증](../validation/2026-10-14/installer-ownership-0151.json)은
모델/GUI 작업 성공이나 입력 지연 통과를 뜻하지 않습니다.

런타임 설치 후 **`Prepare models now? [Y/n]`**으로 모델 준비 여부를 묻습니다. Enter 또는 Y를 누르면 모델 준비를 실행하고, N이면 건너뜁니다. Y를 선택하기 전에 모델 캐시 경로를 설정하세요. 대화형 터미널이 없거나 `--json` 사용 시 기본적으로 건너뜁니다. 자동화에서는 `--prepare-models` 또는 `--skip-models`로 지정할 수 있습니다. 나중에 `clef-use models prepare`를 실행해도 됩니다. `models download`는 가중치만 다운로드합니다.

venv/pip를 포함한 Python 3.11-3.13을 설치하세요. 모델 준비에는 Python 3.11/3.12와 Git이 필요합니다(Windows ROCm은 3.12 필요). root나 관리자 권한은 필요하지 않습니다. 다운로드 URL을 사용하기 전에 공개 호스팅 검증 결과를 확인하세요.

```sh
curl -fsSL https://ftp.kotori9.dev/clef-use/install.sh | sh
```

```powershell
irm https://ftp.kotori9.dev/clef-use/install.ps1 | iex
```

Windows 업데이트는 설치 루트에서 현재 사용자의 명시적·상속 가능한 전체 권한을
확인하면 보존된 이전 버전 전체의 ACL을 다시 쓰지 않습니다. 새 런타임 디렉터리와
모델 준비는 기존 권한 설정을 수행합니다. 권한이 없거나 거부되거나 상속된 권한만
있거나 지원되지 않는 경우에는 기존 grant 경로를 사용하며 권한·timeout 검사를
우회하지 않습니다.

업데이트는 이전 런타임 버전, 모델 캐시와 설정을 보존합니다. 활성화 전에 Ctrl-C로 설치를
중단하면 정리 과정은 사용하지 않는 임시 환경만 삭제하며 기존 런타임은 활성 상태를 유지합니다.
원자적 활성화 전환 후에는 성공 안내가 출력되지 않았더라도 새 활성 환경을 삭제하지 않습니다.
설치 프로그램을 다시 실행해 활성 버전을 확인하세요. 강제 프로세스 종료나 정전은 정리를
건너뛰고 임시 파일을 남길 수 있으며, 충돌 시 내구성과 잔여 파일 자동 삭제는 보장하지 않습니다.

~/.config/clef-use/config.toml을 만들거나 CLEF_USE_CONFIG를 지정하세요. model_dir을 쓰기 가능한 캐시 경로로 바꾸세요. 최소 30 GiB의 여유 공간과 CLEF-Flash 가중치 약 19.1 GB를 처리할 메모리가 필요합니다. 실제 검증 장비는 메모리 48 GiB입니다. 큰 CLEF 모델은 가중치 약 55 GB가 필요하며 여기서는 미검증입니다.

```toml
model_dir = "/path/to/external-ssd/clef-use/models"
device = "auto"
parser_device = "cpu"
max_steps = 30
confidence_threshold = 0.55
```

models prepare는 버전을 고정한 ML 환경 두 개를 만들고 공식 snapshot을 다운로드합니다. 업데이트는 캐시를 보존합니다. Python 3.11 명령이 없으면 --python에 실행 파일의 절대 경로를 지정하세요.

사용할 harness를 하나 선택하고 아래 `codex`를 필요에 따라 `hermes` 또는 `omp`로 바꾸세요. 관리형 통합은 MCP와 선택한 가이드를 함께 설치합니다. harness를 다시 시작한 뒤 검증 단계를 각각 확인하세요. `NOT_RUN`은 작업 성공이 아닙니다.

```sh
clef-use models prepare --python python3.11
clef-use doctor
clef-use integrate codex --dry-run
clef-use integrate codex --scope user
clef-use integrations verify codex --live --read-only
clef-use run 'In the open Calculator, compute 123 * 456' --success 'Calculator shows 56088'
clef-use status
clef-use abort
clef-use update
```

반복 등록 시 관리형 스킬 디렉터리 전체를 가리키는 활성 소스 별칭은 충돌로 처리하지 않습니다.
동명 스킬의 자료 디렉터리가 별개이면 충돌을 보고합니다. `SKILL.md`만 같은 파일을 가리켜도
상대 경로의 참조 자료는 다를 수 있기 때문입니다. 사용자 파일과 설정은 보존합니다.
선택한 소스와 다른 활성 소스 안에서 `SKILL.md`에 선언된 이름이 중복되면,
중첩 디렉터리의 이름이 달라도 충돌을 보고합니다.
Hermes는 설정된 create/external 디렉터리와 현재 신뢰된 Git 프로젝트의
`.hermes/skills`, `.agents/skills`를 확인합니다. 비활성 프로젝트 발견 설정은 유지합니다.
프로젝트를 명시하지 않으면 `TERMINAL_CWD`의 앞뒤 공백과 홈 경로를 처리한 후,
존재하는 디렉터리일 때만 사용합니다. 그 외에는 실행 디렉터리를 사용합니다.
이 보존 검사는 가능한 충돌을 보고하며, 실제 하네스의 발견·로딩 검증은 별도 단계입니다.
Hermes 충돌 검사는 디렉터리 이름 별칭과 기존 이름 기반 Markdown 가이드도 확인합니다.
가이드 내부 자료는 독립 가이드로 검사하지 않습니다. 캐시·의존성 제외 폴더는
`SKILL.md` 목록 검색에서 건너뛰지만, 기존 Markdown은 실제 native 조회로 로딩할 수 있는
위치라면 검사합니다. 잘못된 frontmatter의 이름은 Hermes의 대체 파싱 방식으로 확인합니다.
Hermes MCP 등록은 YAML의 중괄호 매핑, 끝 쉼표, 주석과 문서 종료 표시를 보존하며,
기존 설정과 같은 YAML 문서 안에 등록합니다.
Codex는 개별 `SKILL.md` 항목을 비활성화합니다. 비활성 프로젝트 파일은 활성 관리형
가이드와 충돌하지 않으며, 디렉터리 항목만 지정해도 비활성화된다고 판단하지 않습니다.

macOS에서는 실제 터미널 또는 harness에 화면 기록과 손쉬운 사용 권한을 부여하고 다시 시작하세요. Linux는 접근 가능한 그래픽 화면이 필요하며 Wayland는 캡처와 입력을 제한할 수 있습니다. Windows 패키징은 CI 대상이지만 실제 ML/GUI 호환성은 실험적입니다. 가속 탐지만으로 모델 지원을 입증하지 않습니다.

doctor 실패 시 권한 부족, snapshot 누락, ML 의존성, MCP 시작 오류를 구분하세요. self-test는 모델 없이 제어 흐름을 확인합니다. 설치 프로그램이 Python을 찾지 못하면 CLEF_USE_PYTHON을 지정하세요. LOW_CONFIDENCE와 NEEDS_REPLAN은 상위 계획자의 개입이 필요한 상태이며 ERROR는 완료가 아닙니다.

설치 디렉터리 전체를 삭제하지 말고 `clef-use uninstall`로 관리되는 런타임을 제거하세요.
기본 위치는 POSIX의 `~/.local/share/clef-use`와 `~/.local/bin/clef-use`, Windows의
`%LOCALAPPDATA%\clef-use`입니다. 설치 디렉터리에는 보존해야 할 사용자 데이터도 있을 수
있습니다. 등록까지 제거하려는 경우에만 harness 설정이나 PATH에서 clef-use 항목만 직접
제거하세요. uninstall 명령은 이 등록을 변경하지 않습니다.

[Quick start](QUICKSTART.md) | [Harness](HARNESS_SETUP.md) | [Evidence](../evidence/VALIDATION.md)

0.1.10은 OS/백엔드 기준으로 프로파일을 구성합니다. macOS는 MPS/CPU, Linux와 Windows는 CUDA/ROCm/XPU/CPU가 지원 대상입니다. `models profiles`로 목록을 확인하고 `models prepare --profile linux-cuda`처럼 선택합니다. 지원하지 않는 조합은 거부하며, 전체 모델 초기화가 성공한 후에 설정을 저장합니다. [배포 계약과 검증 범위](../ARCHITECTURE.md#osbackend-deployment-profiles-0110)를 참고하세요. Windows ROCm은 ISA 자동 감지 또는 GPU에 맞는 `--rocm-arch` 설정이 필요합니다.

`models prepare`는 9개 준비 단계, 선택한 백엔드와 캐시 경로, 설치 중인 의존성이나 모델, 캐시 재사용 여부와 경과 시간을 표시합니다. 오래 걸리는 단계는 10초마다 상태를 출력하며, 모델 로딩 중에도 표시됩니다. 단계 수는 전체 소요 시간의 백분율이 아닙니다. 다운로드 전송 진행률은 Hugging Face의 진행 표시가 활성화된 경우 함께 표시됩니다. 단계 안내는 stderr, 최종 JSON 결과는 stdout으로 출력합니다. `models prepare --json`으로 단계 안내를 끌 수 있습니다. 실패하거나 중단된 단계를 알리고, 두 모델의 초기화가 모두 성공한 후에만 설정을 저장합니다.

현재 다운로더는 모든 백엔드에서 원본 Cloudflare snapshot을 받습니다. `--quantization 4bit`는 로딩 시 bitsandbytes NF4를 적용하며, 사전 양자화된 NVFP4 저장소를 선택하지 않습니다. GPU 감지는 추론 환경 프로파일 선택에만 사용됩니다. 현재 로더에는 NVFP4 지원이 없습니다. [커뮤니티 CLEF-Flash NVFP4](https://huggingface.co/kurcontko/clef-flash-NVFP4)는 제작자 안내상 Blackwell GPU와 전용 vLLM 플러그인을 요구하고, 제공 서버는 이미지와 영상 입력을 거부합니다.

## 복구 및 제거

```sh
clef-use doctor --fix
clef-use uninstall
```

`doctor --fix`는 진단 후 누락된 모델·추론 의존성을 기존 준비 경로로 복구하고 다시 확인합니다.
`docker --fix`는 같은 명령의 별칭입니다. 변경된 소스, OS 권한, 화면 연결 문제는
자동으로 덮어쓰지 않고 필요한 조치를 안내합니다. 런타임 종료가 필요한 복구·삭제는 실행 중인
작업이나 모델 hold가 있으면 거부합니다. `uninstall`은 유휴 런타임을 종료하고 관리되는 실행
파일과 런타임 버전만 삭제하며 모델 캐시·추론 환경·설정·MCP 등록·PATH를 보존합니다.
설치 루트 전체를 삭제하지 않습니다. Windows에서는 명령 종료 후 삭제를 예약합니다.
완료로 간주하기 전에 `result`가 지정한 JSON 파일의 `UNINSTALLED` 또는 `ERROR`를 확인하세요.

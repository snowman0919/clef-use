# 설치

venv/pip를 포함한 Python 3.11-3.13을 설치하세요. 모델 준비에는 Python 3.11과 Git이 필요합니다. root나 관리자 권한은 필요하지 않습니다. 다운로드 URL을 사용하기 전에 공개 호스팅 검증 결과를 확인하세요.

```sh
curl -fsSL https://ftp.kotori9.dev/clef-use/install.sh | sh
```

```powershell
irm https://ftp.kotori9.dev/clef-use/install.ps1 | iex
```

~/.config/clef-use/config.toml을 만들거나 CLEF_USE_CONFIG를 지정하세요. model_dir을 쓰기 가능한 캐시 경로로 바꾸세요. 최소 30 GiB의 여유 공간과 CLEF-Flash 가중치 약 19.1 GB를 처리할 메모리가 필요합니다. 실제 검증 장비는 메모리 48 GiB입니다. 큰 CLEF 모델은 가중치 약 55 GB가 필요하며 여기서는 미검증입니다.

```toml
model_dir = "/path/to/external-ssd/clef-use/models"
device = "auto"
parser_device = "cpu"
max_steps = 30
confidence_threshold = 0.55
```

models prepare는 버전을 고정한 ML 환경 두 개를 만들고 공식 snapshot을 다운로드합니다. 업데이트는 캐시를 보존합니다. Python 3.11 명령이 없으면 --python에 실행 파일의 절대 경로를 지정하세요.

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

macOS에서는 실제 터미널 또는 harness에 화면 기록과 손쉬운 사용 권한을 부여하고 다시 시작하세요. Linux는 접근 가능한 그래픽 화면이 필요하며 Wayland는 캡처와 입력을 제한할 수 있습니다. Windows 패키징은 CI 대상이지만 실제 ML/GUI 호환성은 실험적입니다. 가속 탐지만으로 모델 지원을 입증하지 않습니다.

doctor 실패 시 권한 부족, snapshot 누락, ML 의존성, MCP 시작 오류를 구분하세요. self-test는 모델 없이 제어 흐름을 확인합니다. 설치 프로그램이 Python을 찾지 못하면 CLEF_USE_PYTHON을 지정하세요. LOW_CONFIDENCE와 NEEDS_REPLAN은 상위 계획자의 개입이 필요한 상태이며 ERROR는 완료가 아닙니다.

제거하려면 유휴 런타임을 종료하고 관리되는 실행 파일과 설치 디렉터리만 삭제하세요. POSIX는 ~/.local/bin/clef-use와 ~/.local/share/clef-use, Windows는 %LOCALAPPDATA%\clef-use와 해당 사용자 PATH 항목입니다. harness 설정에서는 clef-use만 제거하세요. 명시적으로 삭제하려는 경우가 아니면 캐시와 설정을 보존하세요.

[Quick start](QUICKSTART.md) | [Harness](HARNESS_SETUP.md) | [Evidence](../evidence/VALIDATION.md)

미배포 소스는 OS/백엔드 기준으로 프로파일을 구성합니다. macOS는 MPS/CPU, Linux와 Windows는 CUDA/ROCm/XPU/CPU가 지원 대상입니다. `models profiles`로 목록을 확인하고 `models prepare --profile linux-cuda`처럼 선택합니다. 지원하지 않는 조합은 거부하며, 전체 모델 초기화가 성공한 후에 설정을 저장합니다. [배포 계약과 검증 범위](../ARCHITECTURE.md#osbackend-deployment-profiles-unreleased-source)를 참고하세요. 공개 0.1.8은 기존 Windows 890M 프로파일을 사용합니다.

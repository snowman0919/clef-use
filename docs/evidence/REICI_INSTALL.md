# REICI native Linux release/install/update 검증

## 결과와 범위

- OBSERVED: 2026-10-06(KST), canonical `/home/monad/develop/clef-use`, branch `main`, HEAD `c4a4219b18ac6cc862c84400cab8d33ee2cfb956`와 기존 dirty installer/docs 변경을 직접 검토했다. `/home/monad/develop/prompt.md` 1,090행을 모두 읽었다.
- OBSERVED: Linux x86_64 / Python 3.11.16 네이티브 release를 만들고 실제 다운로드 bootstrap, 독립 venv 설치, 재설치, CLI, doctor, 버전 증가 update, checksum 실패, SIGINT 중단, 실제 MCP stdio initialize/list-tools를 실행했다. 네이티브 테스트를 막는 `scripts/check_installation.py` 결함은 없어서 스크립트/테스트를 수정하지 않았다.
- 이번 worker의 canonical 변경은 이 보고서뿐이다. installer/bootstrap/INSTALL 문서/런타임 수정, git commit/push/topology 변경, GPU/Blender/공유 런타임 조작은 하지 않았다.
- 격리는 전용 설치/설정/상태/캐시 경로와 loopback HTTP를 통한 논리적 격리이며 OS sandbox는 아니다. 테스트 HTTP 서버는 종료되었고, MCP에는 GUI 실행 도구를 호출하지 않았다.

## 아티팩트와 provenance

보존 디렉터리: `/home/monad/develop/reici-production/release/native-linux-py311`

| 아티팩트 | 절대 경로 / 검증 |
|---|---|
| 배포용 native release tree | `/home/monad/develop/reici-production/release/native-linux-py311/site` |
| 제품 ZIP | `/home/monad/develop/reici-production/release/native-linux-py311/site/releases/0.1.21/clef-use-0.1.21-linux-x86_64-py311.zip` |
| 업데이트 전용 fixture tree | `/home/monad/develop/reici-production/release/native-linux-py311/update-fixture` |
| dependency/product wheelhouse | `/home/monad/develop/reici-production/release/native-linux-py311/wheelhouse` |
| source export / 파일별 해시 | `/home/monad/develop/reici-production/release/native-linux-py311/source-export.tar.gz`, `/home/monad/develop/reici-production/release/native-linux-py311/source-sha256.json` |
| 시작 dirty 상태 / 작업 경로 | `/home/monad/develop/reici-production/release/native-linux-py311/baseline-status.txt`, `/home/monad/develop/reici-production/release/native-linux-py311/paths.json` |
| 실제 native harness | `/home/monad/develop/reici-production/release/native-linux-py311/native_e2e.py` |
| 아티팩트 무결성 확인 | `/home/monad/develop/reici-production/release/native-linux-py311/artifact-verification.json` |

빌드 전 git tracked/untracked(non-ignored) 208개 파일을 working-tree 내용 그대로
`/home/monad/.hermes/cache/scratch/reici-native-install-_vaset95/source`로 export했다.
새 git repo를 만들지 않았다. `build_release.py`는 bootstrap을 다시 쓰므로 canonical에서 실행하지 않았다.
빌드 후 export 파일 해시가 모두 같았고, canonical installer/bootstrap/installer tests/네 언어 INSTALL 문서도 시작 해시와 같았다.
제품 wheel 안의 Python 소스는 이 export의 해당 소스와 byte-identical임을 확인했다.
동시 진행되는 main 작업의 최종 통합본이 아니라 위 시점의 dirty snapshot에 대한 증거다.

- MEASURED: 0.1.21 ZIP = 24,232,435 bytes, SHA-256 `9cde6387fb2dfbbb5085d08dda5906bc37ff4e1e6f98c2ab2ef9b1d759fb7eb8`.
- MEASURED: update fixture 0.1.22 ZIP = 24,232,432 bytes, SHA-256 `29dea8ebb4303f2d3993de573122d7bf957c3d83c83d71d2ee538ceb24174e95`.
- OBSERVED: 각 ZIP의 wheel 51개 / hashed requirements 51개 전부 해시가 일치하고 Python 3.11 Linux host tags와 호환된다. `manifest.json`와 `SHA256SUMS`도 일치했다.
- OBSERVED: 기존 wheelhouse는 없었다. pip HTTP cache를 재사용하고 없는 고정 버전만 받아 `requirements/runtime.txt`의 hash 검증 후 wheel을 만들었다. 설치 자체는 실제 `--no-index --only-binary=:all: --require-hashes` 경로다.
- `site`의 manifest URL은 배포 대상 HTTPS origin을 사용한다. local E2E에서는 별도 served copy만 loopback URL로 바꿨다. `update-fixture`의 0.1.22는 source export의 프로젝트 버전만 증가시킨 테스트 릴리스이며 제품 버전으로 publish하면 안 된다. `site`도 이번 native target만 포함하며 다중 OS/Python release 병합이나 외부 업로드는 하지 않았다.

## 실행 명령과 실제 결과

기본 `python`은 3.14.7이라 제품 지원 범위 밖이다. 모든 빌드/테스트는 기존 지원 venv의
`/home/monad/develop/clef-use/.venv/bin/python`(3.11.16)을 사용했다.

Scratch source cwd에서 실행:

```sh
/home/monad/develop/clef-use/.venv/bin/python -m pip wheel --no-build-isolation --require-hashes -r requirements/runtime.txt --wheel-dir /home/monad/.hermes/cache/scratch/reici-native-install-_vaset95/wheelhouse
/home/monad/develop/clef-use/.venv/bin/python scripts/build_release.py --output /home/monad/develop/reici-production/release/native-linux-py311/site --base-url https://ftp.kotori9.dev/clef-use --wheelhouse /home/monad/.hermes/cache/scratch/reici-native-install-_vaset95/wheelhouse
CLEF_USE_NO_MODEL_PROMPT=1 /home/monad/develop/clef-use/.venv/bin/python scripts/check_installation.py --site /home/monad/develop/reici-production/release/native-linux-py311/site --output /home/monad/develop/reici-production/release/native-linux-py311/installation-check.json
```

OBSERVED: 모두 exit 0. 원문 로그는 같은 보존 디렉터리의 `wheelhouse-build.log`,
`build-release.log`, `installation-check.log`; 기존 check 결과는 `installation-check.json`이다.
기존 check에서 `first_install=INSTALLED`, `initial_version=0.1.21`, `idempotent=CURRENT`,
`update=INSTALLED`, `final_version=0.1.22`, bad checksum/missing download/failed version smoke의
launcher 보존 결과가 모두 true였다.

추가 native harness 실행:

```sh
cd /home/monad/.hermes/cache/scratch/reici-native-install-_vaset95
/home/monad/develop/clef-use/.venv/bin/python native_e2e.py
```

OBSERVED: exit 0, `passed=true`. 실제 명령/exit/stdout/stderr/doctor/MCP 결과는
`/home/monad/develop/reici-production/release/native-linux-py311/native-e2e.json`,
요약 stdout은 `/home/monad/develop/reici-production/release/native-linux-py311/native-e2e.log`에 있다.
테스트가 사용한 loopback origin은 `http://127.0.0.1:41563`이고 현재 서버는 종료되었다.
설치 경로는 `/home/monad/.hermes/cache/scratch/reici-native-install-_vaset95/unicode-한글 path/installation`,
launcher는 같은 `unicode-한글 path/bin/clef-use`다.

| 수락 조건 | 실제 관찰 / 판정 |
|---|---|
| 깨끗한 설치 | loopback `curl -fsSL .../install.sh \| sh -s -- --json --skip-models --base-url ... --allow-insecure-localhost`를 pipefail로 실행, `INSTALLED`, version `0.1.21`: MET |
| idempotent 재설치 | 같은 bootstrap을 재실행, `CURRENT`; active pointer/receipt/launcher/version directory 목록/user-data bytes 불변: MET |
| version / CLI startup | 실제 설치 launcher의 `version` exit 0, `self-test` exit 0: MET. self-test는 fixture control-flow이며 GUI/모델 추론 증거가 아님 |
| doctor 진단 실행 | `doctor --no-capture` exit 2, valid JSON, runtime deps 모두 true, MCP OBSERVED, `ready=false`: MET(진단 동작). GUI-ready는 NOT MET/이번 범위 밖 |
| 실제 update | 별도 native 0.1.22 wheel/ZIP을 빌드하고 설치 launcher의 `update` 실행, `INSTALLED`, version `0.1.22`, pointer 교체, 이전 venv와 user-data 보존: MET |
| bad checksum 안전성 | 0.1.23 manifest에 corrupt payload 제공, exit 1와 `SHA-256 mismatch`; pointer/receipt/launcher/versions/config/model-cache/inference-cache sentinel bytes 불변, version `0.1.22`: MET |
| 실제 중단 안전성 | update artifact GET를 HTTP handler에서 대기시킨 뒤 해당 자식 프로세스에 SIGINT, exit 1와 `KeyboardInterrupt`; staged directory 삭제, 이전 pointer/receipt/versions/user-data 불변; 재실행 `CURRENT`: MET(활성화 전) |
| MCP stdio handshake | 실제 설치 launcher `mcp` 자식 프로세스에 SDK client initialize + list-tools; 초기 설치와 update 후 모두 protocol `2025-11-25`, server `clef-use`, 정확히 5개 도구: MET |
| 활성화 직후 중단 | 아래 기존 회귀 테스트의 실제 파일 전환 + `KeyboardInterrupt` fault injection으로 확인: MET(scoped fixture), native 외부 signal의 전환 직후 timing 재현은 NOT_RUN |

MCP 도구는 `computer_abort`, `computer_continue`, `computer_observe`, `computer_run`,
`computer_status`였다. GUI tool call이나 endpoint 생성은 없었다.
별도 비차단 관찰: MCP `serverInfo.version`은 제품 CLI 버전이 아니라 SDK 기본값 `1.30.0`이다.
제품 version 확인은 별도 실제 CLI 출력으로 검증했으며 runtime 파일을 수정하지 않았다.

## Installer 변경 직접 검토 및 회귀 증거

- INFERRED/코드 검토: `src/clef_use/installer.py:421-433`의 cleanup은 성공 flag만 믿지 않고 실제 live pointer를 다시 읽는다. POSIX는 `current.resolve() == staged.resolve()`, Windows는 새 launcher text의 read-back을 사용한다. 원자적 전환 직후 Ctrl-C가 발생해 `activated=True` 대입이 누락된 경우 새 live venv를 지우던 경로를 막는다. SHA-256/manifest/origin/archive 검증과 offline pip 설치 후 smoke, 활성화 순서는 유지된다.
- OBSERVED: export의 installer만 HEAD 버전으로 교체한 별도 scratch `baseline-src`에서 기존 `test_interrupt_after_activation_preserves_live_environment`를 실행했다. POSIX 최초/업데이트와 Windows 최초/업데이트 4개가 모두 `AssertionError: interrupted cleanup deleted the live environment`로 실패했다. 로그: `/home/monad/develop/reici-production/release/native-linux-py311/activation-baseline-red.log`.
- OBSERVED: 현재 export에서 `-k 'interrupt_after_activation or preactivation_failure'`는 `20 passed, 33 deselected`였다. 활성화 전 smoke/activation 오류·KeyboardInterrupt는 staging만 삭제하고, 전환 후 KeyboardInterrupt는 새 live 환경과 기존 user-data를 보존했다. 로그: `/home/monad/develop/reici-production/release/native-linux-py311/activation-current-green.log`.
- OBSERVED: canonical `.venv/bin/python -m pytest tests/test_installer.py -q`는 `53 passed in 1.75s`. 로그: `/home/monad/develop/reici-production/release/native-linux-py311/installer-scoped-tests.log`. full suite는 실행하지 않았다.
- OBSERVED: generated `install.sh`와 PowerShell base64 payload가 canonical Python installer와 일치하는 기존 테스트도 통과했다. Linux 실제 bootstrap은 위 native install로 추가 실행했다. Windows fixture는 플랫폼 분기와 파일 전환을 시뮬레이션하며 네이티브 Windows ACL/CMD/PowerShell 증거가 아니다.
- INFERRED/문서 검토: en/ko/ja/zh-CN의 새 Ctrl-C/강제종료 구분은 이 구현과 일치한다. 제거 안내가 설치 root 전체 삭제 대신 managed `uninstall`로 바뀌어 user-data 보존 계약과 맞는다. CLI `doctor`/`docker` alias 및 `--fix`, maintenance 경로를 읽어 문서의 명령/보존 범위를 검토했다. 이번 설치 worker는 `doctor --fix`/`uninstall`을 실행하지 않았다.
- OBSERVED: scoped `git diff --check` exit 0. 기존 installer/docs 변경을 보존했으며 이번 worker가 발견한 native-test blocker나 수정할 installer 회귀는 없었다.

## 한계 / main 통합 시 유의사항

- NOT_RUN: macOS/Windows 네이티브 설치, Python 3.12/3.13 target, production FTP/HTTPS bootstrap 및 업로드. 이번 증거는 Linux x86_64 Python 3.11뿐이다.
- NOT_RUN: 모델 준비/다운로드/추론, doctor `--fix`, 실제 화면 capture/input, Blender/VRM 및 공유 런타임 작업. 독립 config는 `linux-cpu`로 고정했고 doctor는 `--no-capture`로 실행했다. 모델·ML deps·OmniParser source 부재로 `ready=false`는 의도된 fresh runtime-only 진단이며 GUI 사용 준비 완료를 뜻하지 않는다.
- NOT_RUN: native process에 활성화 직후 정확히 SIGINT를 주는 timing test, SIGKILL/정전/fsync crash durability. 현재 scoped tests는 `os.replace` 직후 예외를 주입한다. 강제 종료는 cleanup을 생략할 수 있고 잔여 staging 자동 회수는 구현되지 않았다.
- 기존 `check_installation.py`의 실패 보존 판정은 주로 launcher bytes라 POSIX active symlink 보존의 단독 증거로는 약하다. 추가 native harness에서 pointer/receipt/version directories/user-data와 실제 version 재실행까지 검사해 보완했다. native 실행을 막는 결함은 아니므로 소유권 제한에 따라 스크립트는 수정하지 않았다.
- `source-export.tar.gz`와 wheelhouse는 scratch가 삭제돼도 빌드 입력/증거를 보존한다. 보존 harness는 one-off 검증용으로 작성됐으며 재실행하려면 fresh scratch에 source export를 풀고 wheelhouse/site를 배치한 뒤 `EVIDENCE` 경로를 새 결과 디렉터리로 설정해야 한다.
- main이 runtime/scene/final integration을 소유한다. 현재 제품 ZIP은 위 snapshot을 고정한 증거이므로 이후 canonical 코드가 변경되면 최종 배포 전 새 source export에서 다시 build/install 검증해야 한다.

## 후속 v2 snapshot의 부모 재검증

- 위 최초 artifact는 역사적 c4a4219+dirty snapshot이다. 후속
  `/home/monad/develop/reici-production/release-v2` artifact는 c62a83e export이며
  둘의 같은 0.1.21 버전 ZIP checksum이 다르다. 동일 immutable release로 혼용하면 안 된다.
- OBSERVED: 부모가 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python
  /home/monad/develop/reici-production/release-v2/final_verify_v2.py`를 직접 재실행해
  exit 0을 확인했다. 출력은 `evidence/release-v2-parent-readback.log`에 있다.
- OBSERVED: activation boundary 20 tests 통과; 두 artifact 모두 wheel51/requirements51,
  host tag 호환·canonical lock 버전·commit export 제품소스 일치, source export 불변을 확인했다.
- MEASURED: v2 Linux py311 0.1.21 ZIP 24,233,135 bytes,
  SHA256 `67fc2885ec69951bfe55485138dc74f69b8f38c39285d1d9c068e12cf667b986`.
- OBSERVED: 격리 설치 launcher가 실제 `0.1.22`를 출력했다. 같은 버전 manifest checksum 변경은
  exit1 `immutable release changed checksum`으로 거부했고 target이 불변이었다.
  모든 테스트 소유 HTTP 서버가 종료되었다. 0.1.22는 여전히 update fixture이며 배포 버전이 아니다.
- NOT_RUN: 후속 empty-OCR/positive-completion-budget 소스 수정의 최종 release 재빌드.
  이 v2 검증은 해당 수정 전 snapshot이며 최신 통합본의 설치 수락으로 확대할 수 없다.
  native Windows/macOS·모든15target·모델/GUI/VRM 수락과 강제종료 내구성도 여전히 미완료다.

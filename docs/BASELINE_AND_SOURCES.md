# 확인한 기준과 공식 근거

작성일: 2026-10-11. 아래는 파일/소스/공식 문서 읽기 결과이며 live 실행 검증이 아니다.

## A. 현재 제품 재확인

저장소: `snowman0919/clef-use`.
현재 main 확인: `b3f0b23309a7c7ea6a943e0c14e0ae51034552cd`.
기존 기획서 기준: `4c725eec736d30eda979298143cd90a61f8a22ee`.
CHANGELOG의 최신 버전: `0.1.29`. 이번 답변에서 공개 설치본을 새로 설치하지 않았다.

이번 확인의 핵심:

- `harness.py`는 Codex/Hermes/OMP의 MCP 설정 등록, 충돌 보호, backup, dry-run,
  프로필/경로 선택을 구현한다. 이 함수는 Agent Skill 배포·발견·읽기 검증은 수행하지 않는다.
- `mcp_server.py`에는 이미 짧은 server instructions와 5개 high-level tool이 있다.
  사용 안내가 전혀 없는 것은 아니다. 다만 별도 스킬 패키지와 사용 능력 검증이 필요하다.
- `HARNESS_SETUP.md`는 MCP 등록과 재시작, 5개 도구 확인을 안내한다.
- 0.1.29는 singleton action 처리와 d1 전체 encoded 8192-token 거부 등 경계 수정을 포함한다.
  인식 개선·GUI 성공·d1 기본값 승격을 주장하지 않는다. 기존 경계 수정은 보존한다.
- 이전 기획의 병목 진단은 PR/HEAD 변경과 실제 실행으로 다시 확인한다.

고정 소스:

1. https://github.com/snowman0919/clef-use/commit/b3f0b23309a7c7ea6a943e0c14e0ae51034552cd
2. https://github.com/snowman0919/clef-use/blob/b3f0b23309a7c7ea6a943e0c14e0ae51034552cd/src/clef_use/harness.py
3. https://github.com/snowman0919/clef-use/blob/b3f0b23309a7c7ea6a943e0c14e0ae51034552cd/src/clef_use/mcp_server.py
4. https://github.com/snowman0919/clef-use/blob/b3f0b23309a7c7ea6a943e0c14e0ae51034552cd/docs/en/HARNESS_SETUP.md
5. https://github.com/snowman0919/clef-use/blob/b3f0b23309a7c7ea6a943e0c14e0ae51034552cd/CHANGELOG.md
6. https://github.com/snowman0919/clef-use/compare/4c725eec736d30eda979298143cd90a61f8a22ee...b3f0b23309a7c7ea6a943e0c14e0ae51034552cd

## B. 사용 스킬과 하네스 공식 자료

### Agent Skills 형식

`SKILL.md`의 name/description, 필요한 자료의 지연 로딩을 공통 형식으로 삼는다.
이것은 조작 실행기나 권한 계층이 아니다.

https://agentskills.io/specification

### Codex

공식 문서는 사용자/repo `.agents/skills` 발견, 명시·암묵적 스킬 선택,
선택적 `agents/openai.yaml`을 설명한다. KODEX라는 임의 파일명 자체를
자동 발견한다고 전제하지 않고 프로젝트 AGENTS에 읽기 지침을 둔다.
공식 재사용 배포 안내는 plugin 패키지도 제시하지만, 이번 최소 구현은
공통 스킬 원본과 설치 어댑터이며 하네스별 실행 로직은 만들지 않는다.

https://developers.openai.com/codex/skills
(조회 시 https://learn.chatgpt.com/docs/build-skills 로 연결)
https://developers.openai.com/codex/guides/agents-md
(조회 시 https://learn.chatgpt.com/docs/agent-configuration/agents-md 로 연결)
https://developers.openai.com/cookbook/articles/codex_exec_plans

### Hermes

공식 문서는 기본 `~/.hermes/skills`, on-demand skill loading, profile과
local/external priority, 기존 사용자 수정 보호를 설명한다.
실제 HERMES_HOME/프로필을 확인하고 같은 이름의 로컬 override를 덮지 않는다.

https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills

### OMP

공식 저장소 docs는 SKILL.md 발견, provider priority, 이름/realpath 중복,
source toggle 및 한 단계 디렉터리 구조를 설명한다.
설치된 버전의 native/agents provider를 확인해 중복 배포를 방지한다.

https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md
https://github.com/can1357/oh-my-pi/blob/main/docs/config-usage.md

### MCP resources

이 문서는 resources가 앱/호스트 중심으로 선택되는 컨텍스트임을 설명한다.
서버가 자료를 등록했다고 모든 모델이 자동으로 읽는다고 가정하지 않는다.
가이드를 resources로도 제공하되 tool instructions와 설치된 스킬을 함께 둔다.

https://modelcontextprotocol.io/specification/2025-06-18/server/resources

## C. 설계 결정을 사실과 분리

KODEX의 새 CLI, `computer_capabilities`, runtime operation, 설치 상태 등급,
성능 예산과 acceptance gate는 이번의 구체화한 설계이다. 공식 표준이나 이미
구현된 제품 기능으로 인용하지 않는다. 구현 전 최신 실제 CLI/schema를 재확인한다.

기존 차세대 기획서에 담긴 MCJev/ActionEngine/GUI-Actor/RTC 등의 연구 근거는
`PRIOR_PLATFORM_PLAN.md`에서 추적한다. 이 패키지가 해당 모델을 설치·실험한 것은 아니다.

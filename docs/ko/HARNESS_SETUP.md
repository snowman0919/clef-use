# Harness 설정

MCP와 Agent Skills를 함께 관리하려면 [에이전트 설정 안내](AGENT_GUIDE.md)를 사용하세요.
사용할 harness를 하나 선택하고 아래 `codex`를 필요에 따라 `hermes` 또는 `omp`로 바꾸세요. 관리형 통합은 MCP와 선택한 가이드를 함께 설치합니다. harness를 다시 시작한 뒤 검증 단계를 각각 확인하세요. `NOT_RUN`은 작업 성공이 아닙니다.

통합은 다른 서버와 주석을 보존하고 수정된 항목을 충돌로 보고합니다. `--dry-run`으로 미리 확인하고 비표준 home/profile은 에이전트 안내에 설명된 환경변수로 선택하세요. 절대 실행 파일 경로는 `--command-path`로 지정합니다. 다시 시작한 뒤 읽기 전용 `computer_capabilities`를 포함한 여섯 도구를 발견하는지 확인하세요. Windows에서 CMD 래퍼를 실행하지 못하는 harness는 활성 버전의 `Scripts/clef-use.exe`를 선택하세요.

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

### Codex

`~/.codex/config.toml` (`CODEX_HOME`):

```toml
[mcp_servers.clef-use]
command = "/absolute/path/to/clef-use"
args = ["mcp"]
tool_timeout_sec = 3600
```

### Hermes

`~/.hermes/config.yaml` (`HERMES_HOME`):

```yaml
mcp_servers:
  clef-use:
    command: /absolute/path/to/clef-use
    args: [mcp]
    timeout: 3600
```

### OMP

`~/.omp/agent/mcp.json` (`PI_CONFIG_DIR`, `PI_CODING_AGENT_DIR`, `OMP_PROFILE`):

```json
{"mcpServers":{"clef-use":{"command":"/absolute/path/to/clef-use",
"args":["mcp"],"type":"stdio","timeout":3600000}}}
```

[Installation](INSTALL.md) | [MCP](MCP.md)

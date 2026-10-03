# Harness 설정

설치기는 다른 서버와 주석을 보존하고 비공개 백업을 만들며 반복 실행 시 중복되지 않습니다. 다른 기존 clef-use 항목은 충돌로 보고하고 덮어쓰지 않습니다. --dry-run으로 미리 확인하고 비표준 경로에는 --path를 사용하세요. 절대 실행 파일 경로를 지정하고 harness를 다시 시작해 다섯 도구를 확인하세요. Windows에서 CMD 래퍼를 실행하지 못하는 harness는 활성 버전의 Scripts/clef-use.exe를 지정하고 업데이트 후 다시 등록하세요.

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

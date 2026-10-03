# Installation

Install Python 3.11-3.13 with venv/pip. Model preparation requires Python 3.11 and Git. No root or Administrator privileges are needed. Public hosting must be verified before using the download URL.

```sh
curl -fsSL https://ftp.kotori9.dev/clef-use/install.sh | sh
```

```powershell
irm https://ftp.kotori9.dev/clef-use/install.ps1 | iex
```

Create ~/.config/clef-use/config.toml or set CLEF_USE_CONFIG. Replace model_dir with a writable cache path. Keep at least 30 GiB free and enough memory for 19.1 GB of CLEF-Flash weights; our actual machine has 48 GiB RAM. The larger CLEF model needs approximately 55 GB of weights and is untested here.

```toml
model_dir = "/path/to/external-ssd/clef-use/models"
device = "auto"
parser_device = "cpu"
max_steps = 30
confidence_threshold = 0.55
```

models prepare creates two isolated pinned environments and downloads canonical upstream snapshots. Updates retain the cache. If Python 3.11 is not discoverable, pass its absolute executable path using --python.

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

Grant Screen Recording and Accessibility to the actual macOS terminal/harness and restart it. Linux requires an accessible graphical display; Wayland may restrict capture/input. Windows packaging is a CI target, while actual ML/GUI compatibility remains experimental. Acceleration detection does not establish model support.

If doctor fails, distinguish permissions, missing snapshots, ML dependencies and MCP startup errors. self-test checks offline control flow. Set CLEF_USE_PYTHON if the installer cannot find a compatible interpreter. LOW_CONFIDENCE and NEEDS_REPLAN require planner intervention; ERROR is not completion.

To uninstall, stop the idle runtime and remove only the managed executable and installation directory: ~/.local/bin/clef-use and ~/.local/share/clef-use on POSIX; %LOCALAPPDATA%\clef-use and its user PATH entry on Windows. Remove only clef-use from harness configs. Keep caches/configs unless you explicitly want to delete them.

[Quick start](QUICKSTART.md) | [Harness](HARNESS_SETUP.md) | [Evidence](../evidence/VALIDATION.md)

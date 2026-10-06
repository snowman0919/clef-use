# Installation

After runtime installation, the installer asks **`Prepare models now? [Y/n]`**. Enter or Y runs model preparation; N skips it. Set the model cache path before accepting Y. Without an interactive terminal, or with `--json`, preparation is skipped by default. Use `--prepare-models` or `--skip-models` to choose explicitly. You can run `clef-use models prepare` later; `models download` downloads weights only.

Install Python 3.11-3.13 with venv/pip. Model preparation requires Python 3.11/3.12 and Git (Windows ROCm requires 3.12). No root or Administrator privileges are needed. Public hosting must be verified before using the download URL.

```sh
curl -fsSL https://ftp.kotori9.dev/clef-use/install.sh | sh
```

```powershell
irm https://ftp.kotori9.dev/clef-use/install.ps1 | iex
```

Updates keep previous runtime versions, model caches and configuration. If Ctrl-C interrupts
installation before activation, cleanup removes only the unused staged environment; an existing
runtime stays active. After the atomic activation switch, cleanup preserves the new live environment
even if the installer did not print success. Rerun the installer to verify the active version.
A forced process kill or power loss can bypass cleanup and leave staging files; crash durability
and automatic removal of those leftovers are not guaranteed.

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
clef-use models prepare --python python3.11
clef-use doctor
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

Use `clef-use uninstall` for managed runtime removal rather than deleting the entire installation
directory. The default runtime locations are `~/.local/share/clef-use` and `~/.local/bin/clef-use`
on POSIX, or `%LOCALAPPDATA%\clef-use` on Windows. The installation directory can also contain
user data that must be kept. Remove only clef-use from harness configs or PATH if you explicitly
want to remove those registrations; the uninstall command leaves them unchanged.

[Quick start](QUICKSTART.md) | [Harness](HARNESS_SETUP.md) | [Evidence](../evidence/VALIDATION.md)

Version 0.1.10 structures deployment profiles by OS/backend: macOS MPS/CPU and Linux/Windows CUDA/ROCm/XPU/CPU. Use `models profiles` to list them and `models prepare --profile linux-cuda` to select one. Unsupported combinations fail explicitly; full worker initialization must pass before configuration is saved. See [deployment contracts and validation limits](../ARCHITECTURE.md#osbackend-deployment-profiles-0110). Windows ROCm requires a detected ISA or `--rocm-arch` for your GPU.

`models prepare` displays nine setup stages, selected backends/cache path,
current dependency/model, cached-model skips and elapsed time. Long stages emit
status every 10 seconds, including model loading. Stage counts are not a total
time percentage. Hugging Face supplies transfer bars when enabled. Stage messages
go to stderr; stdout retains JSON. `models prepare --json` hides stage messages.
Configuration is saved only after both model workers initialize successfully.

## Repair and removal

```sh
clef-use doctor --fix
clef-use uninstall
```

`doctor --fix` diagnoses, repairs missing models and inference dependencies through the existing
preparation path, then checks again. `docker --fix` is an alias of the same command. Modified
source, OS permissions and display connections require the reported manual actions; they are not
automatically overwritten. Active tasks and model holds block repair/removal when runtime shutdown
is required.
`uninstall` stops an idle runtime and removes only the managed launcher and runtime versions.
It preserves model caches, inference environments, configuration, MCP registrations and PATH;
it does not delete the whole installation root. On Windows, removal is scheduled after the command
exits: inspect the JSON file named by `result` for `UNINSTALLED` or `ERROR` before assuming completion.

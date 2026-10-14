# Installation

Since 0.1.51, automatic guide/MCP refresh is limited to registrations owned by
the installation being updated. A fresh installation in a separate root/bin
does not redirect another installation's approved profiles. Modified launchers
and launchers belonging to another root are refused and preserved; choose a
separate `CLEF_USE_BIN_DIR`. Ownership is rechecked under the registration lock.
Use the new installer for that launcher protection: a 0.1.50 bootstrap or CLI
still runs its old installer before the new CLI can apply registration checks. An old
CLI updating its own installation still receives the new CLI's registration
ownership checks. Manual migration can explicitly name `--previous-command`
with `integrations refresh --managed-only --command-path`. See the
[actual package checks](../validation/2026-10-14/installer-ownership-0151.json);
they do not establish native model/GUI success or input latency.

After runtime installation, the installer asks **`Prepare models now? [Y/n]`**. Enter or Y runs model preparation; N skips it. Set the model cache path before accepting Y. Without an interactive terminal, or with `--json`, preparation is skipped by default. Use `--prepare-models` or `--skip-models` to choose explicitly. You can run `clef-use models prepare` later; `models download` downloads weights only.

Install Python 3.11-3.13 with venv/pip. Model preparation requires Python 3.11/3.12 and Git (Windows ROCm requires 3.12). No root or Administrator privileges are needed. Public hosting must be verified before using the download URL.

```sh
curl -fsSL https://ftp.kotori9.dev/clef-use/install.sh | sh
```

```powershell
irm https://ftp.kotori9.dev/clef-use/install.ps1 | iex
```

Windows updates preserve a verified explicit, inheritable full-control grant for
the current user on the installation root, avoiding ACL rewrites across retained
versions. New runtime directories and model preparation still apply their normal
access grants. Missing, denied, inherited-only or unsupported root permissions use
the existing grant path; no permission or timeout check is bypassed.

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

Choose the harness you use: replace `codex` below with `hermes` or `omp`. The managed integration installs MCP and the selected guides together. Restart the harness, then inspect each verification stage; `NOT_RUN` is not task success.

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

Repeat enrollment ignores active-source aliases of the same complete managed
skill directory. A separate resource directory with the same skill name still
reports a conflict, including a symlink of only `SKILL.md`, because relative
references can differ. User files and configuration remain preserved.
Duplicate names declared in `SKILL.md` are also reported within the selected
source and other active sources, even when nested directory names differ.
Hermes checks configured create/external directories and the current trusted Git
project's `.hermes/skills` and `.agents/skills`. Disabled project discovery stays
disabled. Without an explicit project, `TERMINAL_CWD` is trimmed and home-expanded
and used only when it names an existing directory; otherwise the launch directory
is used. These preservation checks report possible conflicts; native discovery
and loading remain separate verification stages.
Hermes collision checks also recognize directory-name aliases and legacy named
Markdown guides. Package support files are not independent guides. Excluded
cache/dependency folders are skipped by the `SKILL.md` catalog, while explicit
legacy Markdown remains checked wherever native lookup can load it. Malformed
frontmatter follows Hermes's name fallback.
Hermes MCP registration preserves YAML flow mappings, trailing commas, comments
and document endings; existing settings remain in the same YAML document.
Codex disables individual `SKILL.md` entries. A disabled project file does not
conflict with the active managed guide; a directory entry alone does not disable it.

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

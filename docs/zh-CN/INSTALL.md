# 安装

运行时安装完成后，会询问 **`Prepare models now? [Y/n]`**。按 Enter 或 Y 执行模型准备，按 N 跳过。接受前请设置模型缓存路径。没有交互终端或使用 `--json` 时默认跳过。自动化可使用 `--prepare-models` 或 `--skip-models` 明确选择，也可稍后运行 `clef-use models prepare`。

请安装带有 venv/pip 的 Python 3.11-3.13。模型准备需要 Python 3.11/3.12 和 Git（Windows ROCm 需要 3.12）。不需要 root 或管理员权限。使用下载 URL 之前，请确认公开部署验证结果。

```sh
curl -fsSL https://ftp.kotori9.dev/clef-use/install.sh | sh
```

```powershell
irm https://ftp.kotori9.dev/clef-use/install.ps1 | iex
```

更新保留旧运行时版本、模型缓存和配置。在激活前按 Ctrl-C 中断安装时，清理只删除未使用的
临时环境，已有运行时仍保持激活。原子切换完成后，即使安装程序尚未显示成功，也会保留
新的活动环境。重新运行安装程序可验证活动版本。强制终止进程或断电可能跳过清理并留下
临时文件；不保证崩溃后的持久性，也不保证自动删除这些残留文件。

创建 ~/.config/clef-use/config.toml，或设置 CLEF_USE_CONFIG。将 model_dir 改为可写缓存目录。至少准备 30 GiB 空间和能处理约 19.1 GB CLEF-Flash 权重的内存。本次设备有 48 GiB 内存。完整 CLEF 权重约 55 GB，在这里未测试。

```toml
model_dir = "/path/to/external-ssd/clef-use/models"
device = "auto"
parser_device = "cpu"
max_steps = 30
confidence_threshold = 0.55
```

models prepare 创建两个固定版本的独立 ML 环境，并下载官方 snapshot。更新保留缓存。如果找不到 Python 3.11 命令，请用 --python 指定可执行文件的绝对路径。

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

macOS 请为实际终端或 harness 授予屏幕录制与辅助功能权限，然后重启。Linux 需要可访问的图形桌面；Wayland 可能限制截图与输入。Windows 打包是 CI 目标，但实际 ML/GUI 兼容性仍属实验性。检测到加速设备不等于模型已经验证。

doctor 失败时，请区分权限、缺失 snapshot、ML 依赖和 MCP 启动错误。self-test 不加载模型，检查控制流程。找不到兼容 Python 时请设置 CLEF_USE_PYTHON。LOW_CONFIDENCE 和 NEEDS_REPLAN 需要规划器介入；ERROR 不表示完成。

请使用 `clef-use uninstall` 移除受管理的运行时，不要删除整个安装目录。默认位置为 POSIX 的
`~/.local/share/clef-use` 和 `~/.local/bin/clef-use`，或 Windows 的 `%LOCALAPPDATA%\clef-use`。
安装目录也可能包含需要保留的用户数据。只有明确要移除注册时，才手动从 harness 配置或
PATH 中删除 clef-use 对应项；uninstall 不会修改这些注册。

[Quick start](QUICKSTART.md) | [Harness](HARNESS_SETUP.md) | [Evidence](../evidence/VALIDATION.md)

0.1.8 的 `models prepare` 在 Windows Radeon 890M (gfx1150) 上自动选择固定的 ROCm/NF4 配置，使用 Python 3.12 和 CPU OmniParser。两个模型成功初始化后才保存配置。可用 `--profile default` 或 `--quantization none` 显式覆盖。实际验证仅包括一个临时 GUI 任务；公开发布状态另行记录。

`models prepare` 显示9个准备阶段、后端及缓存路径、当前依赖或模型、缓存复用和耗时。长时间运行的阶段每10秒输出状态。阶段数量不代表总耗时百分比。使用 `models prepare --json` 可隐藏阶段提示。两个模型均初始化成功后才会保存配置。

## 修复与卸载

```sh
clef-use doctor --fix
clef-use uninstall
```

`doctor --fix` 先诊断，再使用现有准备流程修复缺失的模型和推理依赖，然后重新诊断。
`docker --fix` 是同一命令的别名。修改过的源码、系统权限和显示连接问题会提示手动处理，
不会自动覆盖。需要停止运行时的修复或卸载在存在运行中的任务或模型 hold 时会被拒绝。
`uninstall` 停止空闲运行时，只删除受管理的启动器及运行时版本，保留模型缓存、推理环境、
配置、MCP 注册和 PATH，不删除整个安装根目录。Windows 会安排在命令退出后删除。
认定完成前，请检查 `result` 指定的 JSON 文件中的 `UNINSTALLED` 或 `ERROR`。

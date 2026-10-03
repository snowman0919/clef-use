# 安装

请安装带有 venv/pip 的 Python 3.11-3.13。模型准备需要 Python 3.11 和 Git。不需要 root 或管理员权限。使用下载 URL 之前，请确认公开部署验证结果。

```sh
curl -fsSL https://ftp.kotori9.dev/clef-use/install.sh | sh
```

```powershell
irm https://ftp.kotori9.dev/clef-use/install.ps1 | iex
```

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

macOS 请为实际终端或 harness 授予屏幕录制与辅助功能权限，然后重启。Linux 需要可访问的图形桌面；Wayland 可能限制截图与输入。Windows 打包是 CI 目标，但实际 ML/GUI 兼容性仍属实验性。检测到加速设备不等于模型已经验证。

doctor 失败时，请区分权限、缺失 snapshot、ML 依赖和 MCP 启动错误。self-test 不加载模型，检查控制流程。找不到兼容 Python 时请设置 CLEF_USE_PYTHON。LOW_CONFIDENCE 和 NEEDS_REPLAN 需要规划器介入；ERROR 不表示完成。

卸载时先停止空闲运行时，仅删除托管可执行文件和安装目录：POSIX 为 ~/.local/bin/clef-use 和 ~/.local/share/clef-use；Windows 为 %LOCALAPPDATA%\clef-use 及对应用户 PATH 项。仅移除 harness 的 clef-use 配置。除非明确要删除，否则保留缓存和配置。

[Quick start](QUICKSTART.md) | [Harness](HARNESS_SETUP.md) | [Evidence](../evidence/VALIDATION.md)

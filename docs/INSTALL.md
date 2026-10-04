# Installation

[English](en/INSTALL.md) | [한국어](ko/INSTALL.md) |
[简体中文](zh-CN/INSTALL.md) | [日本語](ja/INSTALL.md)

See the localized instructions for prerequisites, model preparation, permissions,
updates, troubleshooting and removal. Public hosting availability is tracked in
[evidence](evidence/VALIDATION.md). Building and uploading a release is described
in [RELEASE.md](RELEASE.md).

## Runtime installation and model preparation

After runtime installation, the shell/PowerShell installer asks
`Prepare models now? [Y/n]`. Enter or Y runs `models prepare` using the installed
runtime; N skips preparation. `curl | sh` reads the answer from the controlling
terminal. No interactive terminal, EOF and `--json` skip the prompt and model
preparation by default. Use `--prepare-models` or `--skip-models` to choose
explicitly in scripts (including `sh -s -- --skip-models`). Model setup failure
returns a nonzero status while retaining the installed runtime.

Before the first GUI task, choose a writable `model_dir` with enough free space
(including an external SSD if needed), then run:

```sh
clef-use models prepare
clef-use doctor
```

`models prepare` installs inference dependencies, downloads missing models,
initializes the workers and saves configuration. It requires Python 3.11/3.12
and Git. `models download` downloads weights only and does not replace preparation.
Use `clef-use models prepare --help` for Python, profile and quantization options.
Runtime updates retain downloaded models.

`models prepare` reports nine setup stages, the selected backends/cache path,
the current dependency or model being prepared, cached-model skips, and elapsed
time. Long stages emit a status line every 10 seconds, including model loading.
Stage counts identify setup steps, not a percentage of total time.
Download transfer bars are supplied by Hugging Face when enabled. Stage messages
use stderr; stdout retains the JSON result. `models prepare --json` suppresses
setup stage messages. A failed/interrupted stage is identified and configuration
is saved only after both model workers initialize successfully.

The current downloader fetches pinned original Cloudflare snapshots for all
backends. `--quantization 4bit` means bitsandbytes NF4 during loading; it does not
select a pre-quantized NVFP4 repository. GPU detection selects the native runtime
profile, not a different weight artifact. NVFP4 is not implemented in this loader.
The community [CLEF-Flash NVFP4 package](https://huggingface.co/kurcontko/clef-flash-NVFP4)
requires Blackwell hardware and its pinned vLLM plugin; its server rejects image
and video input. Repository existence alone does not establish integration here.

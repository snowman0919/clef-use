import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = """#!/bin/sh
# Generated from src/clef_use/installer.py by scripts/build_installer.py.
set -eu
clef_python="${CLEF_USE_PYTHON:-}"
if [ -z "$clef_python" ]; then
    for candidate in python3.11 python3.12 python3.13 python3; do
        if command -v "$candidate" >/dev/null 2>&1 &&
           "$candidate" -c 'import sys; \
raise SystemExit(not (3,11) <= sys.version_info[:2] < (3,14))' 2>/dev/null; then
            clef_python="$candidate"
            break
        fi
    done
fi
if [ -z "$clef_python" ]; then
    echo 'clef-use: install Python 3.11-3.13 with venv and pip first' >&2
    exit 2
fi
exec "$clef_python" - "$@" <<'CLEF_USE_INSTALLER_PYTHON'
"""


def render():
    source = (ROOT / "src/clef_use/installer.py").read_text()
    return HEADER + source + "\nCLEF_USE_INSTALLER_PYTHON\n"


if __name__ == "__main__":
    (ROOT / "install.sh").write_text(render(), newline="\n")
    (ROOT / "install.sh").chmod(0o755)
    payload = base64.b64encode((ROOT / "src/clef_use/installer.py").read_text().encode()).decode()
    powershell = r"""# Generated from the canonical Python installer; no secondary code download.
$ErrorActionPreference = 'Stop'
$clefPython = $env:CLEF_USE_PYTHON
if (-not $clefPython) {
    foreach ($candidate in @('python3.11', 'python3.12', 'python3.13', 'python')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($command) {
            $probe = 'import sys; raise SystemExit(not (3,11) <= sys.version_info[:2] < (3,14))'
            & $command.Source -c $probe
            if ($LASTEXITCODE -eq 0) { $clefPython = $command.Source; break }
        }
    }
    if (-not $clefPython -and (Get-Command py -ErrorAction SilentlyContinue)) {
        foreach ($minor in @('3.11', '3.12', '3.13')) {
            $resolved = & py "-$minor" -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0) { $clefPython = "$resolved".Trim(); break }
        }
    }
}
if (-not $clefPython) { throw 'Install Python 3.11-3.13 with venv/pip first.' }
if (-not $env:CLEF_USE_INSTALL_ROOT) {
    $env:CLEF_USE_INSTALL_ROOT = Join-Path $env:LOCALAPPDATA 'clef-use'
}
if (-not $env:CLEF_USE_BIN_DIR) {
    $env:CLEF_USE_BIN_DIR = Join-Path $env:CLEF_USE_INSTALL_ROOT 'bin'
}
$source = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__PAYLOAD__'))
$previousEncoding = $OutputEncoding
try {
    $OutputEncoding = New-Object Text.UTF8Encoding $false
    $source | & $clefPython - @args
    if ($LASTEXITCODE -ne 0) {
        throw 'Verified clef-use installation failed; previous runtime retained.'
    }
} finally { $OutputEncoding = $previousEncoding }
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$entries = @($userPath -split ';' | Where-Object { $_ })
if (-not $env:CLEF_USE_NO_PATH_UPDATE -and $entries -notcontains $env:CLEF_USE_BIN_DIR) {
    $updatedPath = ($entries + $env:CLEF_USE_BIN_DIR) -join ';'
    [Environment]::SetEnvironmentVariable('Path', $updatedPath, 'User')
}
if (($env:Path -split ';') -notcontains $env:CLEF_USE_BIN_DIR) {
    $env:Path += ';' + $env:CLEF_USE_BIN_DIR
}
if (@($args) -notcontains '--json' -and -not $env:CLEF_USE_NO_PATH_UPDATE) {
    Write-Host 'Open a new terminal to use clef-use by name if it is not yet on PATH.'
}
"""
    (ROOT / "install.ps1").write_text(powershell.replace("__PAYLOAD__", payload), newline="\n")

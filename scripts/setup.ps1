# PerspectiveBox project setup (Windows).
# Creates .venv, installs the Python package, and optionally installs the
# Virtual Display Driver system-wide (cannot live inside the venv).
#
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
#   powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -SkipVirtualDisplays
#   powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1 -PythonVersion 3.11

[CmdletBinding()]
param(
    [string]$PythonVersion = "3.11",
    [switch]$SkipVirtualDisplays,
    [switch]$SkipVenv
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> PerspectiveBox setup (repo: $Root)"

if (-not $SkipVenv) {
    $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Host "==> Creating .venv with py -$PythonVersion"
        & py "-$PythonVersion" -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create venv. Try -PythonVersion 3.12 or install that Python."
        }
    } else {
        Write-Host "==> Reusing existing .venv"
    }

    Write-Host "==> Upgrading pip and installing perspectivebox[dev] (editable)"
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed"
    }
}

if (-not $SkipVirtualDisplays) {
    Write-Host ""
    Write-Host "==> Virtual Display Driver (system-wide; not part of the venv)"
    $vddScript = Join-Path $PSScriptRoot "install_virtual_displays.ps1"
    & powershell -ExecutionPolicy Bypass -File $vddScript
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Virtual display install did not complete. Python package is still usable with the single-monitor fallback. See Docs/VirtualDisplays.md"
    }
} else {
    Write-Host "==> Skipping virtual displays (-SkipVirtualDisplays)"
}

Write-Host ""
Write-Host "Done. Activate and run:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python scripts\check_displays.py"
Write-Host "  perspectivebox"
Write-Host ""
Write-Host "After VDD install: enable 2 virtual displays in VDC, arrange them in Display Settings."
Write-Host "Details: Docs\VirtualDisplays.md"

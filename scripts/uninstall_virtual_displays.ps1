# Uninstall VirtualDrivers Virtual Display Driver (system-wide) via winget.
# Does not remove the Python .venv or PerspectiveBox package.
#
# Usage (from repo root):
#   powershell -ExecutionPolicy Bypass -File .\scripts\uninstall_virtual_displays.ps1

[CmdletBinding()]
param(
    [string]$WingetId = "VirtualDrivers.Virtual-Display-Driver"
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Host "Virtual Display Driver uninstall"
Write-Host "  Package: $WingetId"
Write-Host "  Note: removes the Windows driver only; .venv is left untouched"
Write-Host ""

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Error "winget not found. Uninstall via Virtual Driver Control (VDC) or Apps > Installed apps instead."
    exit 1
}

if (-not (Test-IsAdmin)) {
    Write-Host "Administrator rights required. Relaunching elevated..."
    $self = $MyInvocation.MyCommand.Path
    $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$self`""
    try {
        $p = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Verb RunAs -Wait -PassThru
        exit $p.ExitCode
    } catch {
        Write-Error "Elevation cancelled or failed. Run this script from an elevated PowerShell."
        exit 1
    }
}

Write-Host "Running: winget uninstall --id=$WingetId -e --disable-interactivity"
& winget uninstall --id=$WingetId -e --disable-interactivity
$code = $LASTEXITCODE
# 0 success; -1978335212 (0x8A150014) often means package not found / already gone
if ($code -eq 0 -or $code -eq -1978335212) {
    Write-Host ""
    Write-Host "Virtual Display Driver package removed (or was not installed)."
    Write-Host "If virtual monitors still appear: open VDC and disable them, or check Device Manager."
    Write-Host "A reboot may be required for DXGI to drop the outputs."
    Write-Host "Verify:  python scripts\check_displays.py"
    exit 0
}

Write-Error "winget uninstall failed with exit code $code. Try uninstalling from VDC or Settings > Apps."
exit $code

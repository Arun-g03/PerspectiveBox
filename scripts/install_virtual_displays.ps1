# Install VirtualDrivers Virtual Display Driver system-wide via winget.
# Display drivers cannot be installed into a Python venv; this is a machine dependency.
#
# Usage (from repo root, preferably elevated PowerShell):
#   powershell -ExecutionPolicy Bypass -File .\scripts\install_virtual_displays.ps1

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

Write-Host "Virtual Display Driver install"
Write-Host "  Package: $WingetId"
Write-Host "  Note: installs to Windows (system-wide), not into .venv"
Write-Host ""

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Error "winget not found. Install App Installer from the Microsoft Store, or use VDC from https://github.com/VirtualDrivers/Virtual-Display-Driver/releases"
    exit 1
}

if (-not (Test-IsAdmin)) {
    Write-Host "Administrator rights required. Relaunching elevated..."
    $self = $MyInvocation.MyCommand.Path
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$self`""
    try {
        $p = Start-Process -FilePath "powershell.exe" -ArgumentList $args -Verb RunAs -Wait -PassThru
        exit $p.ExitCode
    } catch {
        Write-Error "Elevation cancelled or failed. Run this script from an elevated PowerShell."
        exit 1
    }
}

Write-Host "Running: winget install --id=$WingetId -e --accept-package-agreements --accept-source-agreements"
& winget install --id=$WingetId -e --accept-package-agreements --accept-source-agreements
$code = $LASTEXITCODE
# winget returns 0 on success; -1978335189 (0x8A15002B) often means already installed
if ($code -eq 0 -or $code -eq -1978335189) {
    Write-Host ""
    Write-Host "Driver package present."
    Write-Host "Next:"
    Write-Host "  1. Open Virtual Driver Control (VDC) and enable TWO virtual displays (e.g. 1920x1080)."
    Write-Host "  2. Settings > System > Display: arrange virtual | physical | virtual."
    Write-Host "  3. From the repo:  python scripts\check_displays.py"
    Write-Host "  4. See Docs\VirtualDisplays.md"
    exit 0
}

Write-Error "winget install failed with exit code $code"
exit $code

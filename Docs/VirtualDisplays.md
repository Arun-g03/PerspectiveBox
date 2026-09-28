# Virtual displays for three-wall capture

PerspectiveBox maps up to three DXGI outputs to the left / back / right walls. With a single physical monitor, the intended setup is: **one real display + two virtual displays** from a signed IddCx driver. Python cannot invent monitors by itself.

Recommended driver: [VirtualDrivers/Virtual-Display-Driver](https://github.com/VirtualDrivers/Virtual-Display-Driver) (Windows 10/11, winget-installable).

**Important:** a display driver is a Windows kernel component. It **cannot** be installed into a Python `.venv`. The project treats it as a machine dependency installed by the repo setup scripts (same idea as “system deps” next to your venv).

## Install (project scripts)

From the repository root:

```powershell
# Full project setup: .venv + pip install -e ".[dev]" + VDD
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1

# Or driver only (prompts for elevation):
powershell -ExecutionPolicy Bypass -File .\scripts\install_virtual_displays.ps1

# Remove the driver later (does not touch .venv):
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall_virtual_displays.ps1
```

`install_virtual_displays.ps1` runs:

```text
winget install --id=VirtualDrivers.Virtual-Display-Driver -e
```

`uninstall_virtual_displays.ps1` runs:

```text
winget uninstall --id=VirtualDrivers.Virtual-Display-Driver -e
```

### Manual alternatives

1. Install the latest [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) if you do not already have it.
2. Elevated PowerShell:

```powershell
winget install --id=VirtualDrivers.Virtual-Display-Driver -e
```

Or download **Virtual Driver Control (VDC)** from [GitHub Releases](https://github.com/VirtualDrivers/Virtual-Display-Driver/releases), run `VDC.exe` as administrator, and use **Install**.

3. Confirm the adapter appears in **Device Manager → Display adapters** (names vary by release, e.g. Virtual Display Driver / MttVDD).

## Create two virtual monitors

1. Open VDC (or the driver’s control UI).
2. Enable **two** virtual displays (1920×1080 is a good default).
3. Open **Settings → System → Display** and confirm you see **three** monitors total (1 physical + 2 virtual).

## Arrange for PerspectiveBox

PerspectiveBox sorts outputs left-to-right (then top-to-bottom) and maps:

| Wall  | Monitor index |
|-------|---------------|
| Left  | 0 (leftmost)  |
| Back  | 1 (middle)    |
| Right | 2 (rightmost) |

In Display Settings, drag the rectangles so the layout is roughly:

**virtual | physical | virtual**

(or any left-to-right order you prefer). Put app windows on the two virtual screens; keep the PerspectiveBox portal on the physical screen.

## Verify before launching

From the repo root (venv activated):

```powershell
python scripts/check_displays.py
```

You want **3** (or more) DXGI targets listed with distinct `left` positions. Then:

```powershell
perspectivebox
```

Stderr should look like:

```text
PerspectiveBox: 3 display(s); walls left/back/right use monitor indices 0/1/2 ...
```

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| Winget / install fails | Run PowerShell as admin; temporarily disable aggressive antivirus; install via VDC from Releases instead. |
| `vcruntime140.dll` missing | Install the VC++ redistributable (link above). |
| Driver installed but no extra monitors | In Device Manager, ensure the virtual display adapter is **enabled**; re-open VDC and add displays again. |
| Still only 1 DXGI output | Reboot after install; confirm Display Settings shows 3 monitors; run `python scripts/check_displays.py`. |
| Walls show the wrong screens | Re-order monitors left-to-right in Display Settings (PerspectiveBox uses that order). |
| Black / feedback on physical monitor | Portal uses `WDA_EXCLUDEFROMCAPTURE` when available; keep apps on the virtual screens. |
| Want to remove the driver | `powershell -ExecutionPolicy Bypass -File .\scripts\uninstall_virtual_displays.ps1` (reboot if outputs linger). |

## Fallback without the driver

If only one display is present, PerspectiveBox splits that desktop into L/C/R vertical thirds (letterboxed). That is a fallback, not a substitute for real or virtual full displays.

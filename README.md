# PerspectiveBox

Windows-only prototype: webcam head tracking (MediaPipe) drives an off-axis view of your desktop rendered as if you are inside a box whose walls show the live screen capture. Mouse clicks on the portal can be forwarded to the underlying desktop coordinates.  
  
# Why make this?

This program was created mostly for fun—it isn’t intended to solve any real single-screen or multi-screen issues. Most PCs today support multiple desktops and allow you to switch between them, or you can simply have many apps or tabs open and switch as needed. What this program offers is the ability to use a single screen to view multiple windows at the same time, effectively increasing the amount of information you can take in on a single display.
![Example image 1](Docs/Images/Screenshot%202026-03-22%20002551.png)

![Example image 2](Docs/Images/Screenshot%202026-03-22%20002603.png)

![Example image 3](Docs/Images/Screenshot%202026-03-22%20002622.png)
## Requirements

- Windows 10+
- Python 3.10+
- Webcam
- GPU with drivers suitable for OpenGL 3.3 Core and DXGI Desktop Duplication

## Virtual environment / project setup

**One-shot setup** (venv + editable install + virtual display driver):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Flags:

- `-SkipVirtualDisplays` — Python only (single-monitor fallback)
- `-PythonVersion 3.12` — pick a installed `py -X.Y` runtime (default `3.11`)

Manual steps instead:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

If script activation is blocked, use Command Prompt:

```bat
.\.venv\Scripts\activate.bat
```

The virtual display driver is a **Windows system package** (IddCx). It cannot live inside `.venv`; `scripts\setup.ps1` / `scripts\install_virtual_displays.ps1` install it machine-wide via winget (UAC prompt). Use `scripts\uninstall_virtual_displays.ps1` to remove it.

## Run

```powershell
perspectivebox
```

Debug head pose only (prints smoothed normalized coordinates to the terminal):

```powershell
python -m perspectivebox --debug-track
```

## Three-wall setup (recommended)

For a real extended desk (full display per wall), use **one physical monitor + two virtual displays**. See **[Docs/VirtualDisplays.md](Docs/VirtualDisplays.md)**.

Install / re-install the driver only:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_virtual_displays.ps1
```

Uninstall the driver (leaves `.venv` alone):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall_virtual_displays.ps1
```

Verify DXGI outputs before launching:

```powershell
python scripts/check_displays.py
```

## Single monitor (fallback)

With only one display, the desktop is split into three vertical thirds (left | center | right) mapped to the left / back / right walls. Each third is letterboxed onto the wall (not stretched). This is a fallback; prefer virtual displays for full walls.

With three or more outputs (physical and/or virtual), each wall uses a full monitor feed (left-to-right order).

## Recursion guard

The portal window is excluded from Desktop Duplication when the OS allows it (`WDA_EXCLUDEFROMCAPTURE`), so capture shows whatever is behind the window instead of a black rectangle. If that fails, the pipeline falls back to masking out the portal’s screen rectangle.

## Safety

Synthetic mouse input may not reach elevated (Run as administrator) applications. Webcam access requires OS permission.  

# Future

Windows Task View / OS virtual *desktops* (separate from virtual *displays*) remain out of scope; for extra screens use [Docs/VirtualDisplays.md](Docs/VirtualDisplays.md).
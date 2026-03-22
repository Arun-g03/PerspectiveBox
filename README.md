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

## Virtual environment

From the repository root:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If script activation is blocked, use Command Prompt:

```bat
.\.venv\Scripts\activate.bat
```

Install in editable mode:

```powershell
pip install -e ".[dev]"
```

## Run

```powershell
perspectivebox
```

Debug head pose only (prints smoothed normalized coordinates to the terminal):

```powershell
python -m perspectivebox --debug-track
```

## Recursion guard

The capture pipeline masks out the portal window’s screen rectangle in the grabbed frame (filled black) so the texture does not feed back into itself (“hall of mirrors”). For best results, keep the window unobstructed by other apps in that screen region, or use a multi-monitor setup.

## Safety

Synthetic mouse input may not reach elevated (Run as administrator) applications. Webcam access requires OS permission.  

# Future

Add a way to create virtual desktops
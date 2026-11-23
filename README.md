# BenX-AI

🎯 **BenX** - Advanced AI Assistant optimized for **Arch Linux + Hyprland (Wayland)**, with full desktop automation, complete hardware control, multi-model intelligence (Groq & OpenRouter), and a modern GTK4 / Libadwaita glassmorphic UI.

---

## ✨ What's New in V-2.0

### 1. 🪟 Full Hyprland Automation Layer (`jarvis_ai/hyprland/`)
- **Window Management**: Move, resize, float/tile, pin, focus by app name/class/address, close, and tab/group windows via native `hyprctl dispatch`.
- **Workspace Control**: Switch, create, rename, move windows to workspaces or special workspaces (`special:magic`), and cycle workspaces.
- **Layout Templates**: Save entire workspace window setups as JSON templates (`~/.benx/layouts/<name>.json`) and restore them instantly.
- **Monitor Management**: Detect multi-monitor profiles (docked vs. undocked) and assign workspaces across displays.
- **Live Event Automation**: Real-time `socket2.sock` event listener automatically floats Picture-in-Picture windows and moves music apps to designated workspaces.
- **Wayland Peripherals**:
  - Fullscreen, region, and window screenshots via `grim` + `slurp`.
  - Screen recording via `wf-recorder`.
  - Clipboard history, search, and paste via `cliphist`.
  - Notification management (`dunst` / `mako`).
  - Screen lock via `hyprlock`.
- **Dynamic Rules Engine**: Programmatically append window rules to `hyprland_rules.conf` with instant `hyprctl reload`.

### 2. ⚡ Full Laptop & Hardware Control (`jarvis_ai/laptop_control.py`)
- **Power & Battery**: Suspend, hibernate, reboot, shutdown, lock, and manage power profiles (`powerprofilesctl` or sysfs scaling governors). Automatic power-saver engagement on low battery (<15%).
- **Network Management**: Fast Wi-Fi scan, connect, disconnect, and forget via `nmcli`, plus VPN management and IP telemetry.
- **Bluetooth Control**: Device pairing, connection state, trust management, battery levels, and automatic incoming call handling.
- **Process Management**: Top CPU/RAM processes, search, and safe process termination with strict protection for critical system processes (`hyprland`, `systemd`, `pipewire`, etc.).
- **Package Management**: System update checks, package search, installation, and upgrades via `pacman` and `yay` (strictly gated by user confirmation).
- **Input Automation**: Wayland-safe keyboard typing, mouse clicks, and macro replay via `ydotool`.
- **Safe File Operations**: Desktop trash integration (`gio trash` / `trash-cli`), move, copy, and rename.
- **Systemd Management**: User and system service status, start, stop, restart, enable, and disable with critical service guards.

### 3. 🎨 Modern GTK4 + Libadwaita Interface (`jarvis_ai/gui/`)
- **Libadwaita Modern Styling**: Native headerbars, toasts (`Adw.ToastOverlay`), and preferences dialogs (`Adw.PreferencesWindow`).
- **Dual Window Modes**:
  - **Full Dashboard**: System telemetry cards, animated cyberpunk logo, live Hyprland workspace tracker, quick action chips, and rich markdown chat bubbles with copy buttons.
  - **Compact Floating Widget** (`BenX-Compact`): 420x560 pinned floating widget, titlebar handle, mini waveform, quick chips, mic and system audio listener.
  - **Notification Bar** (`BenX-Notification`): Glassmorphic floating notification pill.
- **Voice Waveform Visualizer**: 30fps Cairo animated voice waveform responding to 5 states (`idle`, `listening`, `detected`, `recording`, `thinking`) wired to `WakeWordEngine`.
- **Native Settings Window**: Model selection, API keys, autostart toggle, and Hyprland automation switches.
- **Vector App Iconography**: Vector assets `benx.svg` and `benx-symbolic.svg`.

---

## 🔒 Safety & Guardrails

All destructive operations are strictly gated by confirmation checks in `jarvis_ai/executor.py` (`CONFIRM_ACTIONS`). Operations such as `shutdown`, `reboot`, `suspend`, `hibernate`, `kill_process`, `install_package`, `update_system`, `service_manage`, `file_trash`, `clipboard_wipe`, and `hypr_delete_layout` prompt the user before execution.

---

## 🚀 Quick Start

Use Python 3.10+ on Arch Linux with a running Hyprland session for desktop actions.

```bash
./setup_and_run.sh
```

This installs Python dependencies in `benx_venv` and opens the terminal UI. For other modes, activate the environment first.

```bash
source benx_venv/bin/activate
python benx.py --doctor        # Check available tools and optional features
python benx.py --cli          # Plain text prompt
python benx.py --gtk          # GTK4 / Libadwaita
python benx.py --web          # Local browser UI at http://127.0.0.1:8000
```

- For GTK on Arch, install `gtk4 libadwaita python-gobject python-cairo` with Pacman. To use those Python bindings from the virtual environment, create it with the system Python and `python3 -m venv --system-site-packages benx_venv` before running the setup script. Recreate an existing isolated environment with that option if it cannot import `gi`.
- Install the utilities for the actions you use. Common examples include `grim`, `slurp`, `cliphist`, `wl-clipboard`, `ydotool`, `networkmanager`, and `tesseract`.
- Export `GROQ_API_KEY` or `OPENROUTER_API_KEY` for provider-backed chat. Layout save and restore work without a model key.
- Export `MONGODB_URI` before launch to opt into MongoDB storage. BenX uses local storage by default.

### Try a workspace layout

1. Open two apps and place them on different workspaces.
2. Enter `save my work layout` in the assistant.
3. Move one window, then enter `restore my work layout`. BenX returns matching open windows to their recorded workspaces and reports any missing windows.

The browser UI binds to loopback and prompts in the browser before executing protected actions. For authenticated phone access, see the [Android companion setup](benx_flutter/README.md).

### Run tests

```bash
python -m unittest -v test_benx test_web
```

GTK import tests run when the GTK bindings are installed. The headless tests mock Hyprland and privileged actions.

---

## 🗣️ Natural Language Command Demo List

Try saying or typing any of the following commands into BenX:

### Hyprland Window & Workspace Control
- `"switch to workspace 3"`
- `"move this window to workspace 2"`
- `"toggle floating"`
- `"pin this window"`
- `"move window left"` / `"move window right"`
- `"make window larger"` / `"make window smaller"`
- `"group windows"` / `"switch to next tab"`
- `"tile all windows"`
- `"toggle special workspace"`
- `"save current layout as work"`
- `"restore work layout"`
- `"list layouts"`
- `"show hyprland status"`

### Wayland Peripherals
- `"take a screenshot"`
- `"screenshot a region"`
- `"screenshot this window"`
- `"start screen recording"`
- `"stop recording"`
- `"show clipboard history"`
- `"search clipboard for github"`
- `"paste item 1 from clipboard"`
- `"lock the screen"`

### Laptop & Hardware Management
- `"set power profile to power-saver"` / `"set power profile to performance"`
- `"what is my battery level?"`
- `"scan for wifi networks"`
- `"connect to wifi HomeNetwork password MyPassword"`
- `"show network info"`
- `"list connected bluetooth devices"`
- `"show top processes by cpu"` / `"show top processes by memory"`
- `"kill process 1234"` / `"kill process chrome"`
- `"check for system updates"`
- `"install package vlc"`
- `"move test.txt to trash"`
- `"status of service NetworkManager"`
- `"restart service bluetooth"`

---

## 📄 License
Open source under the MIT License. Built with ❤️ for the Linux & Hyprland community.

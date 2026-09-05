# BenX Architecture & File Structure

## 🎯 Main Entry Points

### **benx.py** ⭐ **MAIN APPLICATION**
```bash
python benx.py          # Start with GTK4 / Libadwaita UI
python benx.py --no-gui # Start in CLI mode
```

### **benx_tui.py** 💻 **MODERN TERMINAL UI**
```bash
python benx_tui.py      # Terminal UI with Rich formatting & system stats
```

### **run_gtk4.py / benx_gtk4.py** 🖥️ **GTK4 RUNNERS**
```bash
python run_gtk4.py      # Pre-loads GTK4 + Libadwaita environments
```

---

## 📁 Package Organization

```
BenX-Assisto/
├── benx.py                   ⭐ Main application entry point
├── benx_tui.py               💻 Terminal UI entry point
├── run_gtk4.py               🖥️ GTK4 application launcher
├── test_benx.py              🧪 Comprehensive test suite (18 tests)
├── hyprland_rules.conf       🪟 Hyprland window rules for BenX widgets
├── TODO_ENHANCEMENTS.md      📋 Progress tracking document
├── FILE_STRUCTURE.md         📁 Architecture reference
├── README.md                 📖 Documentation & user manual
│
├── jarvis_ai/                🧠 Core Python Intelligence & System Control
│   ├── hyprland/             🪟 Modern Hyprland Automation Layer
│   │   ├── __init__.py       Unified HyprlandManager export
│   │   ├── ipc.py            hyprctl JSON queries, dispatches, batch pipelines
│   │   ├── window.py         Window control: move, resize, float, pin, focus, group/tabs
│   │   ├── workspace.py      Workspace management, cycling, layout JSON save/restore
│   │   ├── monitor.py        Multi-monitor detection, docked vs. undocked profiles
│   │   ├── event_listener.py Real-time socket2.sock IPC listener (auto PiP, music WS)
│   │   ├── peripherals.py    grim/slurp screenshot, wf-recorder, cliphist, dunst/mako, hyprlock
│   │   └── rules.py          Dynamic window rule appending & hyprctl hot-reload
│   │
│   ├── gui/                  🎨 Modern GTK4 + Libadwaita User Interface
│   │   ├── assets/           Vector iconography (benx.svg, benx-symbolic.svg)
│   │   ├── settings_window.py Native Adw.PreferencesWindow (models, keys, toggles)
│   │   ├── waveform_widget.py Animated Cairo 30fps voice state visualizer
│   │   ├── beautiful_gtk4.py Full Dashboard, BenX-Compact floating widget, Notifications
│   │   └── beautiful_gtk4.css Glassmorphic styling stylesheet
│   │
│   ├── laptop_control.py     ⚡ Comprehensive Laptop & Hardware Control
│   │   ├── PowerManager      Suspend, hibernate, reboot, shutdown, power profiles
│   │   ├── NetworkManager    nmcli Wi-Fi scan/connect/forget, VPNs, connection telemetry
│   │   ├── ProcessManager    Top processes, search, safe kill with critical guards
│   │   ├── PackageManager    pacman/yay/apt search, updates, install with confirmation
│   │   ├── InputAutomation   Wayland-safe ydotool typing, mouse clicks, hotkey macros
│   │   ├── FileManager       Desktop trash (gio trash/trash-cli), move, copy, rename
│   │   └── ServiceManager    System & user systemd unit status, start, stop, restart
│   │
│   ├── ai_engine.py          🤖 Multi-model AI routing (Groq, OpenRouter)
│   ├── command_engine.py     🗣️ Natural language command parser & intent router
│   ├── executor.py           ⚙️ Command executor with confirmation guards for safety
│   ├── wake_word_engine.py   🎙️ Lightweight wake-word engine with state machine callbacks
│   ├── system_monitor.py     📊 Hardware telemetry (CPU, RAM, battery, network KB/s)
│   ├── bluetooth_manager.py  📶 Bluetooth pairing, device battery, and call handling
│   ├── workspace_monitor.py  🔄 Backward-compatibility facade delegating to jarvis_ai.hyprland
│   ├── automation.py         🤖 Desktop automation utilities
│   ├── mobile_automation.py  📱 Android ADB automation & OCR
│   ├── browser_automation.py 🌐 Web browsing automation
│   ├── config.py             ⚙️ Central configuration and API key manager
│   └── ...
```

---

## 🔒 Safety Architecture
Destructive operations are strictly guarded in `jarvis_ai/executor.py` (`CONFIRM_ACTIONS`). Operations like system shutdown, reboot, package installation, process killing, system service stopping, and file deletion require explicit confirmation via GUI dialog or CLI prompt (`y/N`).

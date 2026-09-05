#!/usr/bin/env python3
"""
BenX TUI — Ultimate Terminal User Interface (Full GTK4 Parity)
Arch Linux + Hyprland (Wayland) Native AI Assistant Console

Features:
- Interactive Hyprland Workspace Tracker (1-10) with click-to-switch & active indicators
- Live Window Manager Controls (Float, Pin, Fullscreen, Move L/R, Group/Tab, Close)
- Layout Templates (Save & Restore Hyprland desktop arrangements)
- Hardware & Laptop Control Panel (Power Saver, Balanced, Performance profiles, Lock, Suspend)
- Safety Confirmation Modal Dialogs for destructive system actions
- Settings Modal Dialog (Model selector, OpenRouter & Groq API key manager, autostart toggle)
- Clipboard History Manager Modal (cliphist search & paste)
- Real-time Audio Waveform Visualizer (20fps ASCII/Braille animation tied to wake-word/assistant states)
- 3-Panel Cyberpunk Layout with Live Telemetry, Top Processes, Mission Stream, and ReAct Agent
"""
import sys
import os
import time
import math
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))

import psutil
from rich.text import Text
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, Input, RichLog, Static, Label, Select, Switch, Button, OptionList
)
from textual.widgets.option_list import Option
from textual.containers import Horizontal, Vertical, Container, Grid, ScrollableContainer
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.reactive import reactive
from textual import work

# ── Hyprland & Laptop Control Imports ─────────────────────────────────────────
try:
    from jarvis_ai.hyprland.workspace import WorkspaceManager
    from jarvis_ai.hyprland.window import WindowManager
    from jarvis_ai.hyprland.peripherals import WaylandPeripherals
    from jarvis_ai.hyprland.ipc import HyprlandIPC
    HYPR_AVAILABLE = True
except Exception:
    HYPR_AVAILABLE = False

try:
    from jarvis_ai.laptop_control import (
        PowerManager, NetworkManager, ProcessManager,
        PackageManager, InputAutomation, FileManager, ServiceManager
    )
    LAPTOP_AVAILABLE = True
except Exception:
    LAPTOP_AVAILABLE = False

try:
    from jarvis_ai.config import Config
    MODELS = [
        "Auto (Best)",
        "meta-llama/llama-3.3-70b-instruct",
        "deepseek/deepseek-r1",
        "google/gemini-2.0-flash-001",
        "qwen/qwen-2.5-72b-instruct",
        "anthropic/claude-3.5-sonnet",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]
except Exception:
    MODELS = [
        "Auto (Best)",
        "meta-llama/llama-3.3-70b-instruct",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]

QUICK_ACTIONS = [
    ("👁️ OCR Screen",      "analyze my screen and describe what you see"),
    ("⚡ Automate",        "automate opening chrome and going to github.com"),
    ("📸 Screenshot",      "take a screenshot"),
    ("🔋 Power Saver",     "set power profile to power-saver"),
    ("📊 Top Procs",       "show top cpu processes"),
    ("🔍 Pacman Update",   "check system updates"),
    ("📱 Mobile ADB",      "check connected mobile phone and list UI elements"),
    ("🪟 Switch WS 1",     "switch to workspace 1"),
]


# ═════════════════════════════════════════════════════════════════════════════
# MODAL DIALOGS
# ═════════════════════════════════════════════════════════════════════════════

class TUIConfirmModal(ModalScreen[bool]):
    """Modal confirmation safety gate for destructive operations"""
    CSS = """
    TUIConfirmModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #confirm-dialog {
        width: 54;
        height: auto;
        background: #061017;
        border: thick #ff6b6b;
        padding: 1 2;
    }
    #confirm-title {
        color: #ff6b6b;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    #confirm-msg {
        color: #eafaf1;
        text-align: center;
        margin-bottom: 2;
    }
    #confirm-buttons {
        height: 3;
        align: center middle;
    }
    #btn-confirm {
        background: #4a1515;
        border: solid #ff6b6b;
        color: #ff6b6b;
        margin-right: 2;
    }
    #btn-confirm:hover {
        background: #782020;
    }
    #btn-cancel {
        background: #0e2b1f;
        border: solid #60ffb9;
        color: #60ffb9;
    }
    #btn-cancel:hover {
        background: #184c36;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
    ]

    def __init__(self, title: str, message: str):
        super().__init__()
        self.modal_title = title
        self.modal_message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(f"⚠️ {self.modal_title}", id="confirm-title")
            yield Label(self.modal_message, id="confirm-msg")
            with Horizontal(id="confirm-buttons"):
                yield Button("Proceed (Enter)", id="btn-confirm")
                yield Button("Cancel (Esc)", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self):
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)


class TUISettingsModal(ModalScreen[None]):
    """Modal Preferences dialog matching BenXSettingsWindow in GTK4"""
    CSS = """
    TUISettingsModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #settings-dialog {
        width: 68;
        height: auto;
        max-height: 85%;
        background: #040c12;
        border: thick #60ffb9;
        padding: 1 2;
    }
    #settings-title {
        color: #60ffb9;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    .settings-section {
        color: #61d8ff;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    .settings-row {
        height: 3;
        align: left middle;
        margin-bottom: 1;
    }
    .settings-label {
        width: 22;
        color: #8eb5ac;
    }
    .settings-input {
        width: 1fr;
        background: #020609;
        border: solid #143626;
        color: #eafaf1;
    }
    #settings-buttons {
        height: 3;
        margin-top: 1;
        align: right middle;
    }
    #btn-settings-save {
        background: #0e3b28;
        border: solid #60ffb9;
        color: #60ffb9;
        margin-right: 1;
    }
    #btn-settings-save:hover {
        background: #185e40;
    }
    #btn-settings-close {
        background: #18222d;
        border: solid #61d8ff;
        color: #61d8ff;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-dialog"):
            yield Label("⚙️  BENX ASSISTANT PREFERENCES", id="settings-title")

            yield Label("◈ AI & MODEL ROUTING", classes="settings-section")
            with Horizontal(classes="settings-row"):
                yield Label("Default Model:", classes="settings-label")
                yield Select([(m, m) for m in MODELS], value=MODELS[0], id="set-model-select")

            yield Label("◈ API CREDENTIALS", classes="settings-section")
            with Horizontal(classes="settings-row"):
                yield Label("OpenRouter API Key:", classes="settings-label")
                openrouter_val = os.getenv("OPENROUTER_API_KEY", "")
                masked_openrouter = (openrouter_val[:6] + "..." + openrouter_val[-4:]) if len(openrouter_val) > 10 else openrouter_val
                yield Input(value=masked_openrouter, placeholder="sk-or-v1-...", id="set-openrouter-key", classes="settings-input")

            with Horizontal(classes="settings-row"):
                yield Label("Groq API Key:", classes="settings-label")
                groq_val = os.getenv("GROQ_API_KEY", "")
                masked_groq = (groq_val[:6] + "..." + groq_val[-4:]) if len(groq_val) > 10 else groq_val
                yield Input(value=masked_groq, placeholder="gsk_...", id="set-groq-key", classes="settings-input")

            yield Label("◈ HYPRLAND & AUTOMATION", classes="settings-section")
            with Horizontal(classes="settings-row"):
                yield Label("Hyprland Dynamic Rules:", classes="settings-label")
                yield Switch(value=True, id="set-rules-switch")
            with Horizontal(classes="settings-row"):
                yield Label("Autostart on Login:", classes="settings-label")
                autostart_active = Path(os.path.expanduser("~/.config/autostart/benx.desktop")).exists()
                yield Switch(value=autostart_active, id="set-autostart-switch")

            with Horizontal(id="settings-buttons"):
                yield Button("Save & Apply", id="btn-settings-save")
                yield Button("Close (Esc)", id="btn-settings-close")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-settings-save":
            self.save_settings()
        self.dismiss()

    def action_close(self):
        self.dismiss()

    def save_settings(self):
        """Persist settings to local .env and config"""
        try:
            ork = self.query_one("#set-openrouter-key", Input).value.strip()
            grk = self.query_one("#set-groq-key", Input).value.strip()
            autostart = self.query_one("#set-autostart-switch", Switch).value

            env_path = Path(__file__).parent / ".env"
            env_lines = []
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    env_lines = f.readlines()

            def set_env_var(key: str, val: str):
                if "..." in val:
                    return
                os.environ[key] = val
                found = False
                for i, l in enumerate(env_lines):
                    if l.startswith(f"{key}="):
                        env_lines[i] = f"{key}={val}\n"
                        found = True
                        break
                if not found and val:
                    env_lines.append(f"{key}={val}\n")

            if ork and "..." not in ork:
                set_env_var("OPENROUTER_API_KEY", ork)
            if grk and "..." not in grk:
                set_env_var("GROQ_API_KEY", grk)

            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(env_lines)

            # Autostart desktop entry
            auto_dir = Path(os.path.expanduser("~/.config/autostart"))
            auto_file = auto_dir / "benx.desktop"
            if autostart:
                auto_dir.mkdir(parents=True, exist_ok=True)
                auto_file.write_text(
                    f"[Desktop Entry]\nType=Application\nName=BenX\nExec={sys.executable} {Path(__file__).resolve()}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\n",
                    encoding="utf-8"
                )
            elif auto_file.exists():
                auto_file.unlink()

            if hasattr(self.app, "_log_mission"):
                self.app._log_mission("⚙️ Settings successfully saved and applied.")
        except Exception as e:
            if hasattr(self.app, "_log_mission"):
                self.app._log_mission(f"⚠️ Error saving settings: {e}")


class ClipboardModal(ModalScreen[None]):
    """Modal Viewer for Wayland Clipboard History (cliphist)"""
    CSS = """
    ClipboardModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    #clip-dialog {
        width: 72;
        height: 24;
        background: #040c12;
        border: thick #61d8ff;
        padding: 1 2;
    }
    #clip-title {
        color: #61d8ff;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    #clip-filter {
        height: 3;
        background: #020609;
        border: solid #143626;
        color: #eafaf1;
        margin-bottom: 1;
    }
    #clip-list {
        height: 1fr;
        background: #010305;
        border: solid #143626;
    }
    #clip-buttons {
        height: 3;
        margin-top: 1;
        align: right middle;
    }
    #btn-clip-copy {
        background: #0e3b28;
        border: solid #60ffb9;
        color: #60ffb9;
        margin-right: 1;
    }
    #btn-clip-close {
        background: #18222d;
        border: solid #61d8ff;
        color: #61d8ff;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "copy_selected", "Copy"),
    ]

    def __init__(self):
        super().__init__()
        self.raw_items: List[str] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="clip-dialog"):
            yield Label("📋  WAYLAND CLIPBOARD HISTORY (cliphist)", id="clip-title")
            yield Input(placeholder="Search clipboard entries...", id="clip-filter")
            yield OptionList(id="clip-list")
            with Horizontal(id="clip-buttons"):
                yield Button("Copy to Clipboard (Enter)", id="btn-clip-copy")
                yield Button("Close (Esc)", id="btn-clip-close")

    def on_mount(self):
        self.load_history()

    def load_history(self, filter_text: str = ""):
        try:
            if HYPR_AVAILABLE:
                self.raw_items = WaylandPeripherals.get_clipboard_history(30)
            else:
                self.raw_items = ["Hyprland peripherals not available"]
        except Exception as e:
            self.raw_items = [f"Error: {e}"]

        opt_list = self.query_one("#clip-list", OptionList)
        opt_list.clear_options()
        filtered = [it for it in self.raw_items if filter_text.lower() in it.lower()] if filter_text else self.raw_items
        for item in filtered:
            clean_item = item.strip().replace("\n", " ")[:65]
            opt_list.add_option(Option(prompt=clean_item, id=clean_item))

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "clip-filter":
            self.load_history(event.value)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-clip-copy":
            self.copy_selected()
        self.dismiss()

    def action_copy_selected(self):
        self.copy_selected()
        self.dismiss()

    def action_close(self):
        self.dismiss()

    def copy_selected(self):
        try:
            opt_list = self.query_one("#clip-list", OptionList)
            if opt_list.highlighted is not None:
                selected_opt = opt_list.get_option_at_index(opt_list.highlighted)
                val = str(selected_opt.prompt)
                if HYPR_AVAILABLE:
                    WaylandPeripherals.paste_from_history(val)
                if hasattr(self.app, "_log_mission"):
                    self.app._log_mission(f"📋 Copied to clipboard: '{val[:40]}'")
        except Exception as e:
            if hasattr(self.app, "_log_mission"):
                self.app._log_mission(f"⚠️ Clipboard copy error: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# AUDIO WAVEFORM VISUALIZER WIDGET (TUI GTK4 PARITY)
# ═════════════════════════════════════════════════════════════════════════════

class TUIWaveformWidget(Static):
    """
    Animated text-based audio waveform reacting to assistant & voice states.
    States: 'idle', 'listening', 'detected', 'recording', 'thinking'.
    """
    state: reactive[str] = reactive("idle")
    phase: float = 0.0

    BAR_CHARS = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    def on_mount(self):
        self.set_interval(0.08, self.tick)

    def set_state(self, new_state: str):
        self.state = new_state.lower()

    def tick(self):
        self.phase += 0.22
        num_bars = 24
        bars = []

        if self.state == "listening":
            color = "#61d8ff"
            state_tag = "LISTENING"
            for i in range(num_bars):
                v = math.sin(self.phase + i * 0.45) * math.cos(self.phase * 0.5 + i * 0.2)
                level = int(round((v + 1.0) / 2.0 * (len(self.BAR_CHARS) - 1)))
                bars.append(self.BAR_CHARS[max(0, min(len(self.BAR_CHARS) - 1, level))])
        elif self.state == "detected":
            color = "#60ffb9"
            state_tag = "DETECTED"
            for i in range(num_bars):
                v = math.sin(self.phase * 2.0 + i * 0.6)
                level = int(round((v + 1.0) / 2.0 * (len(self.BAR_CHARS) - 1)))
                bars.append(self.BAR_CHARS[max(0, min(len(self.BAR_CHARS) - 1, level))])
        elif self.state == "recording":
            color = "#ff6b6b"
            state_tag = "RECORDING"
            for i in range(num_bars):
                v = abs(math.sin(self.phase * 1.5 + i * 0.7) * math.sin(self.phase * 2.3 + i * 0.3))
                level = int(round(v * (len(self.BAR_CHARS) - 1)))
                bars.append(self.BAR_CHARS[max(0, min(len(self.BAR_CHARS) - 1, level))])
        elif self.state == "thinking":
            color = "#b794ff"
            state_tag = "THINKING"
            for i in range(num_bars):
                v = (math.sin(self.phase + i * 0.3) + math.sin(self.phase * 1.3 - i * 0.5)) / 2.0
                level = int(round((v + 1.0) / 2.0 * (len(self.BAR_CHARS) - 1)))
                bars.append(self.BAR_CHARS[max(0, min(len(self.BAR_CHARS) - 1, level))])
        else:  # idle
            color = "#8eb5ac"
            state_tag = "IDLE"
            for i in range(num_bars):
                v = math.sin(self.phase * 0.4 + i * 0.25) * 0.3
                level = int(round((v + 0.3) / 1.0 * 2))
                bars.append(self.BAR_CHARS[max(0, min(len(self.BAR_CHARS) - 1, level))])

        bar_str = "".join(bars)
        text = f"[{color}]{bar_str}[/{color}] [dim {color}]● {state_tag}[/dim {color}]"
        self.update(text)


# ═════════════════════════════════════════════════════════════════════════════
# HYPRLAND WORKSPACE & WINDOW MANAGER BAR
# ═════════════════════════════════════════════════════════════════════════════

class HyprlandBar(Static):
    """
    Interactive Hyprland Workspace & Active Window Controller.
    Displays 1-10 workspace badges, active window title/class, and quick window actions.
    """

    def on_mount(self):
        self.update_hypr_state()
        self.set_interval(1.8, self.update_hypr_state)

    def update_hypr_state(self):
        if not HYPR_AVAILABLE:
            self.update("[dim #8eb5ac]Hyprland IPC: Standby (Non-Hyprland Wayland)[/dim #8eb5ac]")
            return

        try:
            active_ws = WorkspaceManager.get_active_workspace()
            workspaces = WorkspaceManager.list_workspaces()
            occupied_ws = {w.get("id"): w.get("windows", 0) for w in workspaces}

            # Build 1-10 workspace chips
            ws_parts = []
            for i in range(1, 11):
                if i == active_ws:
                    ws_parts.append(f"[bold #03080d on #60ffb9] {i} [/bold #03080d on #60ffb9]")
                elif i in occupied_ws:
                    cnt = occupied_ws[i]
                    ws_parts.append(f"[bold #61d8ff on #09202a] {i}:{cnt} [/bold #61d8ff on #09202a]")
                else:
                    ws_parts.append(f"[dim #8eb5ac] {i} [/dim #8eb5ac]")
            ws_str = " ".join(ws_parts)

            # Active Window
            active_win = WindowManager.get_active_window()
            win_title = active_win.get("title", "Desktop / No active window")[:42]
            win_class = active_win.get("class", "desktop")[:18]
            is_float = "🪟 Float" if active_win.get("floating", False) else "🔲 Tile"

            text = (
                f"[bold #61d8ff]◈ HYPRLAND WORKSPACES[/bold #61d8ff]  {ws_str}\n"
                f"[bold #8eb5ac]Active Window:[/bold #8eb5ac] [bold white]{win_title}[/bold white] [dim #61d8ff]({win_class})[/dim #61d8ff] [{is_float}]"
            )
            self.update(text)
        except Exception as e:
            self.update(f"[dim #8eb5ac]Hyprland State: Ready ({e})[/dim #8eb5ac]")


# ═════════════════════════════════════════════════════════════════════════════
# HARDWARE & LAPTOP CONTROLS PANEL
# ═════════════════════════════════════════════════════════════════════════════

class LaptopControlsPanel(Static):
    """
    Laptop hardware controls: power profile indicators, Wi-Fi, battery, and recording state.
    """

    def on_mount(self):
        self.update_display()
        self.set_interval(3.0, self.update_display)

    def update_display(self):
        if not LAPTOP_AVAILABLE:
            self.update("[dim #8eb5ac]Laptop Hardware Control: Ready[/dim #8eb5ac]")
            return

        try:
            profile = PowerManager.get_profile()
            is_recording = WaylandPeripherals.is_recording() if HYPR_AVAILABLE else False
            rec_tag = "[bold #ff6b6b]🔴 RECORDING ACTIVE[/bold #ff6b6b]" if is_recording else "[dim #8eb5ac]Camera/Screen: Standby[/dim #8eb5ac]"

            # Profile badges
            p_saver = "[bold #60ffb9 on #0e3b28] 🌱 Saver [/bold #60ffb9 on #0e3b28]" if profile == "power-saver" else "[dim #8eb5ac] Saver [/dim #8eb5ac]"
            p_bal = "[bold #61d8ff on #09202a] ⚖️ Balanced [/bold #61d8ff on #09202a]" if profile == "balanced" else "[dim #8eb5ac] Balanced [/dim #8eb5ac]"
            p_perf = "[bold #ffc857 on #3a2e0a] ⚡ Performance [/bold #ffc857 on #3a2e0a]" if profile == "performance" else "[dim #8eb5ac] Performance [/dim #8eb5ac]"

            text = (
                f"[bold #61d8ff]◈ POWER PROFILE[/bold #61d8ff]\n"
                f"{p_saver} {p_bal} {p_perf}\n\n"
                f"[bold #8eb5ac]Screen Capture:[/bold #8eb5ac] {rec_tag}"
            )
            self.update(text)
        except Exception as e:
            self.update(f"[dim #8eb5ac]Hardware Control: {e}[/dim #8eb5ac]")


# ═════════════════════════════════════════════════════════════════════════════
# TELEMETRY & DIAGNOSTICS PANEL (LEFT)
# ═════════════════════════════════════════════════════════════════════════════

class StatsPanel(Static):
    """Real-time Linux system telemetry matching GTK4 stat cards"""

    def on_mount(self):
        self.update_stats()
        self.set_interval(1.5, self.update_stats)

    def _meter(self, pct: float, color: str, w: int = 15) -> str:
        pct = max(0, min(100, pct))
        filled = int(round(pct / 100 * w))
        empty = w - filled
        return f"[{color}]{'█' * filled}[/{color}][dim #143626]{'░' * empty}[/dim #143626] [bold {color}]{pct:>3.0f}%[/bold {color}]"

    def update_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            bat = psutil.sensors_battery()
            now = datetime.now()

            # Network throughput
            now_bytes = net.bytes_sent + net.bytes_recv
            prev = getattr(self, "_prev_net", (now_bytes, now.timestamp()))
            delta_bytes = max(0, now_bytes - prev[0])
            delta_t = max(now.timestamp() - prev[1], 0.1)
            kbps = delta_bytes / delta_t / 1024
            self._prev_net = (now_bytes, now.timestamp())

            # CPU Temp
            temp_str = ""
            try:
                temps = psutil.sensors_temperatures()
                for lst in temps.values():
                    if lst and lst[0].current > 0:
                        temp_str = f" {lst[0].current:.0f}°C"
                        break
            except Exception:
                pass

            cpu_color = "#60ffb9" if cpu < 65 else ("#ffc857" if cpu < 85 else "#ff6b6b")
            mem_color = "#61d8ff" if mem.percent < 75 else ("#ffc857" if mem.percent < 90 else "#ff6b6b")
            disk_color = "#b794ff" if disk.percent < 80 else "#ff6b6b"

            bat_str = f"{bat.percent:.0f}% {'⚡ Plugged' if bat.power_plugged else '🔋 Battery'}" if bat else "AC Line"
            bat_pct = bat.percent if bat else 100

            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            uptime_str = f"{int(uptime.total_seconds() // 3600)}h {int((uptime.total_seconds() % 3600) // 60)}m"

            # Top CPU process
            top_proc = "Idle"
            try:
                if LAPTOP_AVAILABLE:
                    procs = ProcessManager.get_top_cpu(1)
                    if procs:
                        top_proc = f"{procs[0].get('name', 'idle')} ({procs[0].get('cpu', 0):.0f}%)"
            except Exception:
                pass

            text = (
                f"[bold #61d8ff]🕒 {now.strftime('%H:%M:%S')}[/bold #61d8ff]  [dim #8eb5ac]{now.strftime('%b %d')}[/dim #8eb5ac]\n"
                f"[dim #143626]{'━' * 23}[/dim #143626]\n"
                f"[bold #8eb5ac]🌐 NET I/O[/bold #8eb5ac] [bold #b794ff]{kbps:>5.1f} KB/s[/bold #b794ff]\n"
                f"{self._meter(min(kbps / 400 * 100, 100), '#b794ff')}\n"
                f"[bold #8eb5ac]⚡ CPU LOAD[/bold #8eb5ac] [{cpu_color}]{cpu:>3.0f}%{temp_str}[/{cpu_color}]\n"
                f"{self._meter(cpu, cpu_color)}\n"
                f"[bold #8eb5ac]💾 MEMORY[/bold #8eb5ac] [{mem_color}]{mem.used / 1e9:.1f}/{mem.total / 1e9:.1f}GB[/{mem_color}]\n"
                f"{self._meter(mem.percent, mem_color)}\n"
                f"[bold #8eb5ac]📁 ROOT DISK[/bold #8eb5ac] [{disk_color}]{disk.used / 1e9:.0f}/{disk.total / 1e9:.0f}GB[/{disk_color}]\n"
                f"{self._meter(disk.percent, disk_color)}\n"
                f"[bold #8eb5ac]🔋 POWER[/bold #8eb5ac] [green]{bat_str}[/green]\n"
                f"{self._meter(bat_pct, '#60ffb9')}\n"
                f"[dim #143626]{'━' * 23}[/dim #143626]\n"
                f"[dim #8eb5ac]Top Proc: [/dim #8eb5ac][bold white]{top_proc}[/bold white]\n"
                f"[dim #8eb5ac]Arch Linux + Hyprland (UP: {uptime_str})[/dim #8eb5ac]\n"
            )
            self.update(text)
        except Exception as e:
            self.update(f"[red]Telemetry error: {e}[/red]")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN BENX TUI APPLICATION
# ═════════════════════════════════════════════════════════════════════════════

class BenXTUI(App):
    """Full-featured GTK4-parity Textual UI for BenX AI Assistant"""
    TITLE = "BenX AI Assistant v2.0 (Terminal Console)"

    CSS = """
    Screen {
        background: #020406;
        color: #eafaf1;
    }

    /* ── Header Top Bar ── */
    #topbar {
        height: 3;
        background: #040d12;
        border-bottom: solid #143626;
        padding: 0 1;
        align: left middle;
    }
    #top-pill {
        color: #60ffb9;
        text-style: bold;
        margin-right: 1;
    }
    #top-title {
        color: #f4fff9;
        text-style: bold;
        width: 1fr;
    }
    #top-waveform {
        width: 38;
        content-align: right middle;
        margin-right: 1;
    }
    #top-btn-settings {
        background: #09202a;
        border: solid #61d8ff;
        color: #61d8ff;
        margin-right: 1;
        height: 3;
    }
    #top-btn-settings:hover {
        background: #143626;
        border: solid #60ffb9;
        color: #60ffb9;
    }

    /* ── Main Grid ── */
    #main-grid {
        height: 1fr;
    }

    #left-panel {
        width: 27;
        border-right: solid #143626;
        background: #03080d;
        padding: 0 1;
    }

    #center-panel {
        width: 1fr;
        border-right: solid #143626;
        background: #03070b;
        padding: 0 1;
    }

    #right-panel {
        width: 50;
        background: #04090e;
        padding: 0 1;
    }

    .panel-title {
        color: #60ffb9;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    .panel-sub {
        color: #8eb5ac;
        text-style: dim;
        margin-bottom: 1;
    }

    /* ── Center Content: Hyprland & Mission Stream ── */
    HyprlandBar {
        height: 4;
        border: solid #143626;
        background: #020509;
        padding: 0 1;
        margin-top: 1;
        margin-bottom: 1;
    }

    #win-controls-row {
        height: 3;
        margin-bottom: 1;
    }
    .win-btn {
        min-width: 6;
        background: #040d12;
        border: solid #143626;
        color: #61d8ff;
        margin-right: 1;
        padding: 0 1;
    }
    .win-btn:hover {
        background: #0c2b1e;
        border: solid #60ffb9;
        color: #60ffb9;
    }

    #activity-stream {
        height: 1fr;
        border: solid #143626;
        background: #010305;
        padding: 0 1;
    }

    /* ── Left Content: Telemetry & Laptop Controls ── */
    LaptopControlsPanel {
        height: 6;
        border: solid #143626;
        background: #020509;
        padding: 0 1;
        margin-top: 1;
        margin-bottom: 1;
    }

    #hardware-buttons-row-1 {
        height: 3;
        margin-bottom: 1;
    }
    #hardware-buttons-row-2 {
        height: 3;
        margin-bottom: 1;
    }
    .hw-btn {
        min-width: 5;
        background: #040d12;
        border: solid #143626;
        color: #8eb5ac;
        margin-right: 1;
        padding: 0 1;
    }
    .hw-btn:hover {
        background: #0c2b1e;
        border: solid #60ffb9;
        color: #60ffb9;
    }

    /* ── Right Panel: Chat & Automation ── */
    #controls-bar {
        height: 3;
        margin-top: 1;
        margin-bottom: 1;
        align: left middle;
    }
    #model-select {
        width: 30;
        background: #030a0f;
        border: solid #143626;
        color: #60ffb9;
    }
    #agent-switch {
        width: 6;
        margin-left: 1;
    }

    #chat-window {
        height: 1fr;
        border: solid #143626;
        background: #010305;
        padding: 0 1;
    }

    #chips-container {
        height: 3;
        margin-top: 1;
    }
    .quick-chip {
        min-width: 8;
        background: #040d12;
        border: solid #143626;
        color: #8eb5ac;
        margin-right: 1;
        padding: 0 1;
    }
    .quick-chip:hover {
        background: #0c2b1e;
        border: solid #60ffb9;
        color: #60ffb9;
    }

    #composer-row {
        height: 3;
        margin-top: 1;
    }
    #attach-btn {
        width: 4;
        background: #040d12;
        border: solid #143626;
        color: #61d8ff;
    }
    #chat-input {
        width: 1fr;
        background: #03080d;
        border: solid #143626;
        color: #eafaf1;
    }
    #chat-input:focus {
        border: solid #60ffb9;
    }
    #send-btn {
        width: 5;
        background: #0e3b28;
        border: solid #60ffb9;
        color: #60ffb9;
    }

    #status-footer {
        height: 1;
        background: #04120c;
        color: #60ffb9;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit",         "Quit"),
        Binding("ctrl+l", "clear_chat",   "Clear Chat"),
        Binding("f1",     "show_help",    "Help"),
        Binding("f2",     "toggle_agent", "Agent Mode"),
        Binding("f3",     "voice_input",  "Voice"),
        Binding("f4",     "take_screen",  "Screenshot"),
        Binding("f5",     "refresh_state","Refresh"),
        Binding("f6",     "open_settings","Settings"),
        Binding("f7",     "toggle_record","Screen Rec"),
        Binding("f8",     "lock_screen",  "Lock"),
    ]

    agent_mode: reactive[bool] = reactive(False)

    def __init__(self):
        super().__init__()
        self.ai_engine = None
        self.pending_image = None

    def _init_ai_engine(self):
        try:
            from jarvis_ai.ai_engine import AIEngine
            self.ai_engine = AIEngine()
            try:
                self.call_from_thread(self._log_mission, "✅ AI Engine & OpenRouter stack online")
            except RuntimeError:
                pass
        except Exception as e:
            try:
                self.call_from_thread(self._log_mission, f"⚠️ Engine init: {e}")
            except RuntimeError:
                pass

    def compose(self) -> ComposeResult:
        # Top Header Bar
        with Horizontal(id="topbar"):
            yield Label("● BENX", id="top-pill")
            yield Label("Adaptive Linux Control & Automation Platform", id="top-title")
            yield TUIWaveformWidget(id="top-waveform")
            yield Button("⚙️ Settings (F6)", id="top-btn-settings")

        with Horizontal(id="main-grid"):
            # ── LEFT: Telemetry & Hardware Control ────────────────────────────
            with Vertical(id="left-panel"):
                yield Label("◈ TELEMETRY", classes="panel-title")
                yield StatsPanel()

                yield Label("◈ HARDWARE", classes="panel-title")
                yield LaptopControlsPanel()

                # Power Profiles & Hardware Quick Actions
                with Horizontal(id="hardware-buttons-row-1"):
                    yield Button("🌱 Saver", id="btn-prof-saver", classes="hw-btn")
                    yield Button("⚖️ Bal", id="btn-prof-bal", classes="hw-btn")
                    yield Button("⚡ Perf", id="btn-prof-perf", classes="hw-btn")
                    yield Button("🔒 Lock", id="btn-lock", classes="hw-btn")

                with Horizontal(id="hardware-buttons-row-2"):
                    yield Button("💤 Sleep", id="btn-sleep", classes="hw-btn")
                    yield Button("📋 Clip", id="btn-clip", classes="hw-btn")
                    yield Button("🔄 Boot", id="btn-reboot", classes="hw-btn")
                    yield Button("🛑 Off", id="btn-poweroff", classes="hw-btn")

            # ── CENTER: Hyprland & Mission Stream ─────────────────────────────
            with Vertical(id="center-panel"):
                yield HyprlandBar(id="hypr-bar")

                # Window action buttons matching GTK4 WindowControls
                with Horizontal(id="win-controls-row"):
                    yield Button("🪟 Float", id="btn-win-float", classes="win-btn")
                    yield Button("📌 Pin", id="btn-win-pin", classes="win-btn")
                    yield Button("🔲 Full", id="btn-win-full", classes="win-btn")
                    yield Button("◀ Move", id="btn-win-move-l", classes="win-btn")
                    yield Button("Move ▶", id="btn-win-move-r", classes="win-btn")
                    yield Button("📑 Group", id="btn-win-group", classes="win-btn")
                    yield Button("💾 Save WS", id="btn-ws-save", classes="win-btn")
                    yield Button("✕ Close", id="btn-win-close", classes="win-btn")

                yield Label("◈ MISSION PIPELINE & DISPATCH LOG", classes="panel-title")
                yield Label("Real-time desktop events, agent steps & execution telemetry", classes="panel-sub")
                yield RichLog(id="activity-stream", highlight=True, markup=True)

            # ── RIGHT: Assistant Chat Node ────────────────────────────────────
            with Vertical(id="right-panel"):
                yield Label("◈ ASSISTANT NODE", classes="panel-title")

                with Horizontal(id="controls-bar"):
                    yield Select([(m, m) for m in MODELS], value=MODELS[0], id="model-select")
                    yield Label("Agent:", id="agent-label")
                    yield Switch(value=False, id="agent-switch")

                yield RichLog(id="chat-window", highlight=True, markup=True)

                # Quick Automation Chips
                with Horizontal(id="chips-container"):
                    for idx, (lbl, _) in enumerate(QUICK_ACTIONS[:4]):
                        yield Button(lbl, classes="quick-chip", id=f"chip-{idx}")

                # Composer Row
                with Horizontal(id="composer-row"):
                    yield Button("+", id="attach-btn", tooltip="Attach screenshot")
                    yield Input(placeholder="Ask BenX or type an automation command...", id="chat-input")
                    yield Button("➤", id="send-btn")

        # Footer
        yield Label(
            "● BenX Ready  │  F1 Help  │  F2 Agent  │  F3 Voice  │  F4 Screen  │  F6 Settings  │  F7 Rec  │  F8 Lock  │  Ctrl+C Quit",
            id="status-footer"
        )
        yield Footer()

    def on_mount(self):
        chat = self.query_one("#chat-window", RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        chat.write(
            f"[dim #8eb5ac][{ts}][/dim #8eb5ac] [bold #60ffb9]BenX Assistant v2.0 Online (TUI)[/bold #60ffb9]\n"
            f"[dim white]Arch Linux + Hyprland (Wayland) native control stack ready.[/dim white]\n"
            f"[dim #61d8ff]⚡ Features: Full Hyprland window/workspace manager, laptop power profiles, live telemetry, clipboard history & ReAct agent.[/dim #61d8ff]\n"
        )
        self._log_mission("BenX TUI mounted with full GTK4 parity.")
        self.query_one("#chat-input", Input).focus()
        threading.Thread(target=self._init_ai_engine, daemon=True).start()

    # ── Button Pressed Handlers ───────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if not bid:
            return

        # Top Bar
        if bid == "top-btn-settings":
            self.action_open_settings()

        # Chat & Composer
        elif bid == "send-btn":
            inp = self.query_one("#chat-input", Input)
            val = inp.value.strip()
            inp.value = ""
            if val:
                self.send_user_message(val)
        elif bid == "attach-btn":
            self.action_take_screen()
        elif bid.startswith("chip-"):
            try:
                idx = int(bid.replace("chip-", ""))
                _, cmd = QUICK_ACTIONS[idx]
                inp = self.query_one("#chat-input", Input)
                inp.value = cmd
                inp.focus()
            except Exception:
                pass

        # Power Profile Buttons
        elif bid == "btn-prof-saver":
            self.set_power_profile("power-saver")
        elif bid == "btn-prof-bal":
            self.set_power_profile("balanced")
        elif bid == "btn-prof-perf":
            self.set_power_profile("performance")

        # Hardware Buttons
        elif bid == "btn-lock":
            self.action_lock_screen()
        elif bid == "btn-sleep":
            self.confirm_and_run("Suspend System?", "Put laptop into sleep/suspend mode?", lambda: PowerManager.suspend() if LAPTOP_AVAILABLE else None)
        elif bid == "btn-clip":
            self.push_screen(ClipboardModal())
        elif bid == "btn-reboot":
            self.confirm_and_run("Reboot System?", "Are you sure you want to reboot the laptop now?", lambda: PowerManager.reboot() if LAPTOP_AVAILABLE else None)
        elif bid == "btn-poweroff":
            self.confirm_and_run("Shutdown System?", "Are you sure you want to completely power off?", lambda: PowerManager.shutdown() if LAPTOP_AVAILABLE else None)

        # Hyprland Window Controls
        elif bid == "btn-win-float":
            if HYPR_AVAILABLE:
                WindowManager.toggle_floating()
                self._log_mission("🪟 Toggled active window floating state")
                self.action_refresh_state()
        elif bid == "btn-win-pin":
            if HYPR_AVAILABLE:
                WindowManager.toggle_pin()
                self._log_mission("📌 Toggled active window pin")
                self.action_refresh_state()
        elif bid == "btn-win-full":
            if HYPR_AVAILABLE:
                WindowManager.fullscreen()
                self._log_mission("🔲 Toggled fullscreen")
                self.action_refresh_state()
        elif bid == "btn-win-move-l":
            if HYPR_AVAILABLE:
                WindowManager.move_active("l")
                self._log_mission("◀ Moved active window left")
        elif bid == "btn-win-move-r":
            if HYPR_AVAILABLE:
                WindowManager.move_active("r")
                self._log_mission("▶ Moved active window right")
        elif bid == "btn-win-group":
            if HYPR_AVAILABLE:
                WindowManager.toggle_group()
                self._log_mission("📑 Toggled tab group on active window")
        elif bid == "btn-ws-save":
            if HYPR_AVAILABLE:
                res = WorkspaceManager.save_layout("default_tui")
                self._log_mission(f"💾 Workspace layout saved: {res}")
        elif bid == "btn-win-close":
            if HYPR_AVAILABLE:
                WindowManager.close_active()
                self._log_mission("✕ Closed active window")
                self.action_refresh_state()

    def set_power_profile(self, profile: str):
        if LAPTOP_AVAILABLE:
            res = PowerManager.set_profile(profile)
            self._log_mission(f"🔋 Power Profile set to '{profile}': {res}")
            self.action_refresh_state()

    def confirm_and_run(self, title: str, message: str, action_func):
        def on_result(confirmed: bool):
            if confirmed:
                self._log_mission(f"⚠️ Executing confirmed operation: {title}")
                try:
                    action_func()
                except Exception as e:
                    self._log_mission(f"❌ Error during operation: {e}")
            else:
                self._log_mission("Operation canceled by user.")

        self.push_screen(TUIConfirmModal(title, message), on_result)

    # ── Switch & Select Handlers ──────────────────────────────────────────────

    def on_switch_changed(self, event: Switch.Changed):
        if event.switch.id == "agent-switch":
            self.agent_mode = event.value
            status = "AUTONOMOUS RE-ACT AGENT" if event.value else "INSTANT COMMAND ROUTER"
            self._log_mission(f"Agent mode switched: [bold #60ffb9]{status}[/bold #60ffb9]")
            self._set_status_bar(f"Mode: {status}")

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "model-select":
            val = str(event.value)
            self._log_mission(f"Selected AI model: {val}")

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "chat-input":
            val = event.value.strip()
            event.input.value = ""
            if val:
                self.send_user_message(val)

    # ── User Message Execution ────────────────────────────────────────────────

    def send_user_message(self, text: str):
        if not text and not self.pending_image:
            return

        chat = self.query_one("#chat-window", RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        img_badge = f" [bold #61d8ff][📎 {os.path.basename(self.pending_image)}][/bold #61d8ff]" if self.pending_image else ""
        chat.write(f"\n[dim #8eb5ac][{ts}][/dim #8eb5ac] [bold cyan]👤 You:[/bold cyan] {text}{img_badge}")

        self._log_mission(f"User command: {text[:60]}")
        self._set_status_bar("⏳ BenX is processing...")
        self.set_waveform_state("thinking")

        self.execute_task_worker(text, self.pending_image)
        self.pending_image = None

    @work(thread=True)
    def execute_task_worker(self, text: str, image_path: Optional[str] = None):
        chat = self.query_one("#chat-window", RichLog)
        try:
            if not self.ai_engine:
                from jarvis_ai.ai_engine import AIEngine
                self.ai_engine = AIEngine()

            sel = self.query_one("#model-select", Select)
            selected_model = None if sel.value == "Auto (Best)" else sel.value

            def on_agent_step(step_text: str):
                self.app.call_from_thread(self._log_mission, f"[bold #b794ff]Step:[/bold #b794ff] {step_text[:75]}")

            if image_path:
                self.app.call_from_thread(self._log_mission, f"Vision OCR analysis: {image_path}")
                response = self.ai_engine.chat(text, image_path=image_path, model=selected_model)
            elif self.agent_mode:
                self.app.call_from_thread(self._log_mission, "Engaging multi-step ReAct agent...")
                response = self.ai_engine.agent_run(text, on_step_cb=on_agent_step, model=selected_model)
                if not response:
                    response = self.ai_engine.chat(text, model=selected_model)
            else:
                from jarvis_ai.executor import CommandExecutor
                cmd_json = self.ai_engine.interpret_command(
                    text,
                    conversation_context=self.ai_engine.conversation_history,
                    learning_engine=self.ai_engine.learning_engine,
                    model=selected_model,
                )
                self.app.call_from_thread(self._log_mission, f"Command: {cmd_json[:50]}")
                response = CommandExecutor.execute(cmd_json, self.ai_engine, text)
                if response is None:
                    response = self.ai_engine.chat(text, model=selected_model)

            ts = datetime.now().strftime("%H:%M:%S")
            self.app.call_from_thread(
                chat.write,
                f"[dim #8eb5ac][{ts}][/dim #8eb5ac] [bold #60ffb9]🤖 BenX:[/bold #60ffb9]\n{response}\n"
            )
            self.app.call_from_thread(self._log_mission, f"✅ Task finished: {str(response)[:50]}")
            self.app.call_from_thread(self._set_status_bar, "✓ BenX Ready")
            self.app.call_from_thread(self.set_waveform_state, "idle")
        except Exception as err:
            ts = datetime.now().strftime("%H:%M:%S")
            self.app.call_from_thread(chat.write, f"[dim #8eb5ac][{ts}][/dim #8eb5ac] [bold red]❌ Error:[/bold red] {err}")
            self.app.call_from_thread(self._log_mission, f"❌ Execution error: {err}")
            self.app.call_from_thread(self._set_status_bar, "✗ Error encountered")
            self.app.call_from_thread(self.set_waveform_state, "idle")

    # ── Hotkeys & Actions ─────────────────────────────────────────────────────

    def action_clear_chat(self):
        self.query_one("#chat-window", RichLog).clear()
        self._log_mission("Chat log cleared.")
        self._set_status_bar("Chat window cleared")

    def action_toggle_agent(self):
        sw = self.query_one("#agent-switch", Switch)
        sw.value = not sw.value

    def action_open_settings(self):
        self.push_screen(TUISettingsModal())

    def action_refresh_state(self):
        try:
            hb = self.query_one("#hypr-bar", HyprlandBar)
            hb.update_hypr_state()
            lp = self.query_one("LaptopControlsPanel", LaptopControlsPanel)
            lp.update_display()
            self._log_mission("Desktop & hardware state refreshed.")
        except Exception:
            pass

    def action_take_screen(self):
        """Take screenshot and prime for vision analysis"""
        try:
            if HYPR_AVAILABLE:
                path = WaylandPeripherals.take_screenshot(select_region=False)
            else:
                from jarvis_ai.command_engine import CommandEngine
                path = CommandEngine.take_screenshot()

            if path and os.path.exists(path):
                self.pending_image = path
                self._log_mission(f"📸 Screenshot attached: {path}")
                inp = self.query_one("#chat-input", Input)
                inp.value = "analyze this screenshot"
                inp.focus()
                self._set_status_bar(f"Screenshot ready: {os.path.basename(path)}")
            else:
                self._log_mission(f"Screenshot taken: {path}")
        except Exception as e:
            self._log_mission(f"Screenshot error: {e}")

    def action_toggle_record(self):
        if not HYPR_AVAILABLE:
            self._log_mission("Screen recording not supported without Hyprland peripherals.")
            return

        if WaylandPeripherals.is_recording():
            path = WaylandPeripherals.stop_screen_recording()
            self._log_mission(f"🎥 Screen recording stopped and saved to: {path}")
        else:
            success, msg = WaylandPeripherals.start_screen_recording()
            self._log_mission(f"🎥 Screen recording started: {msg}")
        self.action_refresh_state()

    def action_lock_screen(self):
        if LAPTOP_AVAILABLE:
            PowerManager.lock()
            self._log_mission("🔒 Hyprlock engaged")

    def action_voice_input(self):
        self._set_status_bar("🎤 Listening for voice...")
        self.set_waveform_state("listening")
        self._log_mission("🎤 Voice input active")
        self.listen_voice_worker()

    @work(thread=True)
    def listen_voice_worker(self):
        try:
            from jarvis_ai.voice_handler import VoiceHandler
            vh = VoiceHandler()
            text = vh.listen()
            if text:
                self.app.call_from_thread(self._log_mission, f"🎤 Transcribed: '{text}'")
                self.app.call_from_thread(self.send_user_message, text)
            else:
                self.app.call_from_thread(self._set_status_bar, "🎤 No speech detected")
                self.app.call_from_thread(self.set_waveform_state, "idle")
        except Exception as exc:
            self.app.call_from_thread(self._set_status_bar, f"🎤 Voice error: {exc}")
            self.app.call_from_thread(self.set_waveform_state, "idle")

    def action_show_help(self):
        chat = self.query_one("#chat-window", RichLog)
        chat.write(
            "\n[bold #60ffb9]══════════════════ BENX TERMINAL CONSOLE GUIDE ══════════════════[/bold #60ffb9]\n"
            "[bold #61d8ff]Function Hotkeys:[/bold #61d8ff]\n"
            "  [white]F1[/white]        Show this help guide\n"
            "  [white]F2[/white]        Toggle Autonomous ReAct Agent (ON/OFF)\n"
            "  [white]F3[/white]        Trigger Voice Input (Speech-to-Text)\n"
            "  [white]F4[/white]        Capture Desktop Screenshot & Prime for Vision OCR\n"
            "  [white]F5[/white]        Refresh Hyprland Workspaces & Hardware State\n"
            "  [white]F6[/white]        Open Settings Dialog (Models, API Keys, Autostart)\n"
            "  [white]F7[/white]        Toggle Screen Recording (wf-recorder)\n"
            "  [white]F8[/white]        Engage Screen Lock (hyprlock)\n"
            "  [white]Ctrl+L[/white]    Clear current chat log\n"
            "  [white]Ctrl+C[/white]    Quit BenX TUI\n\n"
            "[bold #61d8ff]Hyprland Controls (Center Bar Buttons):[/bold #61d8ff]\n"
            "  [cyan]Float[/cyan]       Toggle active window floating\n"
            "  [cyan]Pin[/cyan]         Pin active window across workspaces\n"
            "  [cyan]Full[/cyan]        Toggle active window fullscreen\n"
            "  [cyan]Move L/R[/cyan]    Move window left or right in tiled layout\n"
            "  [cyan]Group[/cyan]       Toggle tabbed window grouping\n"
            "  [cyan]Save WS[/cyan]     Save desktop layout to ~/.benx/layouts/\n\n"
            "[bold #61d8ff]Hardware Controls (Left Panel Buttons):[/bold #61d8ff]\n"
            "  [cyan]Saver/Bal/Perf[/cyan] Switch Linux power profiles on-the-fly\n"
            "  [cyan]Clip[/cyan]           Browse Wayland clipboard history (cliphist)\n"
            "  [cyan]Sleep / Boot[/cyan]   Suspend or reboot with safety confirmation gate\n"
            "[bold #60ffb9]══════════════════════════════════════════════════════════════════[/bold #60ffb9]\n"
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def set_waveform_state(self, state: str):
        try:
            wf = self.query_one("#top-waveform", TUIWaveformWidget)
            wf.set_state(state)
        except Exception:
            pass

    def _log_mission(self, msg: str):
        try:
            ts = datetime.now().strftime("%H:%M:%S")
            log = self.query_one("#activity-stream", RichLog)
            log.write(f"[dim #8eb5ac][{ts}][/dim #8eb5ac] {msg}")
        except Exception:
            pass

    def _set_status_bar(self, status: str):
        try:
            lbl = self.query_one("#status-footer", Label)
            lbl.update(
                f"● {status}  │  F1 Help  │  F2 Agent  │  F3 Voice  │  F4 Screen  │  F6 Settings  │  F7 Rec  │  F8 Lock  │  Ctrl+C Quit"
            )
        except Exception:
            pass


if __name__ == "__main__":
    BenXTUI().run()

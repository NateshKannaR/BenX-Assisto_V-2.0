#!/usr/bin/env python3
"""
BenX TUI — Modern, Clean Terminal AI Assistant
Arch Linux + Hyprland (Wayland) Native Console

Features:
- Clean, modern Obsidian/Tokyo-Night aesthetic with subtle borders and card styling
- Spacious primary AI conversation view with rich markdown formatting and syntax highlighting
- Clean telemetry sidebar with real-time btop-style meters (CPU, RAM, Disk, Net, Battery)
- Live Hyprland desktop integration (workspaces, active window, window actions)
- Laptop hardware control (power profiles, screen lock, clipboard manager, sleep)
- Animated audio waveform visualizer (20fps reactive ASCII bars)
- Interactive modal preferences (F6) and safety confirmation gates
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
    Input, RichLog, Static, Label, Select, Switch, Button, OptionList
)
from textual.widgets.option_list import Option
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.reactive import reactive
from textual import work

# ── Hyprland & System Imports ────────────────────────────────────────────────
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
    ("⚡ Automate",        "automate opening chrome and going to github.com"),
    ("📸 Screenshot",      "take a screenshot"),
    ("👁️ Screen OCR",      "analyze my screen and describe what you see"),
    ("🔋 Power Saver",     "set power profile to power-saver"),
    ("📊 Top Procs",       "show top cpu processes"),
    ("🔍 Check Updates",   "check system updates"),
    ("📱 Mobile ADB",      "check connected mobile phone and list UI elements"),
    ("🪟 Workspaces",      "list workspaces"),
]


# ═════════════════════════════════════════════════════════════════════════════
# MODAL SCREENS (MODERN CLEAN DESIGN)
# ═════════════════════════════════════════════════════════════════════════════

class TUIConfirmModal(ModalScreen[bool]):
    """Clean modern safety confirmation modal"""
    CSS = """
    TUIConfirmModal {
        align: center middle;
        background: rgba(10, 14, 20, 0.85);
    }
    #confirm-box {
        width: 50;
        height: auto;
        background: #161b22;
        border: round #f85149;
        padding: 1 2;
    }
    #confirm-header {
        color: #f85149;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    #confirm-body {
        color: #e6edf3;
        text-align: center;
        margin-bottom: 2;
    }
    #confirm-actions {
        height: 3;
        align: center middle;
    }
    #btn-yes {
        background: #da3633;
        color: #ffffff;
        border: none;
        margin-right: 2;
    }
    #btn-yes:hover {
        background: #f85149;
    }
    #btn-no {
        background: #21262d;
        color: #c9d1d9;
        border: none;
    }
    #btn-no:hover {
        background: #30363d;
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
        with Vertical(id="confirm-box"):
            yield Label(f"⚠️  {self.modal_title}", id="confirm-header")
            yield Label(self.modal_message, id="confirm-body")
            with Horizontal(id="confirm-actions"):
                yield Button("Proceed (Enter)", id="btn-yes")
                yield Button("Cancel (Esc)", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self):
        self.dismiss(True)

    def action_cancel(self):
        self.dismiss(False)


class TUISettingsModal(ModalScreen[None]):
    """Clean, modern preferences dialog"""
    CSS = """
    TUISettingsModal {
        align: center middle;
        background: rgba(10, 14, 20, 0.85);
    }
    #settings-box {
        width: 66;
        height: auto;
        max-height: 85%;
        background: #161b22;
        border: round #38bdf8;
        padding: 1 2;
    }
    #settings-header {
        color: #38bdf8;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    .cfg-group {
        color: #7ee787;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }
    .cfg-row {
        height: 3;
        align: left middle;
        margin-bottom: 1;
    }
    .cfg-label {
        width: 22;
        color: #8b949e;
    }
    .cfg-input {
        width: 1fr;
        background: #0d1117;
        border: round #30363d;
        color: #f0f6fc;
    }
    .cfg-input:focus {
        border: round #38bdf8;
    }
    #settings-actions {
        height: 3;
        margin-top: 1;
        align: right middle;
    }
    #btn-cfg-save {
        background: #238636;
        color: #ffffff;
        border: none;
        margin-right: 1;
    }
    #btn-cfg-save:hover {
        background: #2ea043;
    }
    #btn-cfg-close {
        background: #21262d;
        color: #c9d1d9;
        border: none;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="settings-box"):
            yield Label("⚙️  BenX Preferences", id="settings-header")

            yield Label("Model Routing", classes="cfg-group")
            with Horizontal(classes="cfg-row"):
                yield Label("Default Model:", classes="cfg-label")
                yield Select([(m, m) for m in MODELS], value=MODELS[0], id="set-model-select")

            yield Label("API Credentials", classes="cfg-group")
            with Horizontal(classes="cfg-row"):
                yield Label("OpenRouter Key:", classes="cfg-label")
                openrouter_val = os.getenv("OPENROUTER_API_KEY", "")
                masked_openrouter = (openrouter_val[:6] + "..." + openrouter_val[-4:]) if len(openrouter_val) > 10 else openrouter_val
                yield Input(value=masked_openrouter, placeholder="sk-or-v1-...", id="set-openrouter-key", classes="cfg-input")

            with Horizontal(classes="cfg-row"):
                yield Label("Groq Key:", classes="cfg-label")
                groq_val = os.getenv("GROQ_API_KEY", "")
                masked_groq = (groq_val[:6] + "..." + groq_val[-4:]) if len(groq_val) > 10 else groq_val
                yield Input(value=masked_groq, placeholder="gsk_...", id="set-groq-key", classes="cfg-input")

            yield Label("System Automation", classes="cfg-group")
            with Horizontal(classes="cfg-row"):
                yield Label("Hyprland Rules:", classes="cfg-label")
                yield Switch(value=True, id="set-rules-switch")
            with Horizontal(classes="cfg-row"):
                yield Label("Autostart on Login:", classes="cfg-label")
                autostart_active = Path(os.path.expanduser("~/.config/autostart/benx.desktop")).exists()
                yield Switch(value=autostart_active, id="set-autostart-switch")

            with Horizontal(id="settings-actions"):
                yield Button("Save Changes", id="btn-cfg-save")
                yield Button("Close", id="btn-cfg-close")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-cfg-save":
            self.save_settings()
        self.dismiss()

    def action_close(self):
        self.dismiss()

    def save_settings(self):
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

            if hasattr(self.app, "_log"):
                self.app._log("⚙️ Preferences updated and saved.")
        except Exception as e:
            if hasattr(self.app, "_log"):
                self.app._log(f"⚠️ Preferences error: {e}")


class ClipboardModal(ModalScreen[None]):
    """Clean Wayland clipboard history modal"""
    CSS = """
    ClipboardModal {
        align: center middle;
        background: rgba(10, 14, 20, 0.85);
    }
    #clip-box {
        width: 70;
        height: 22;
        background: #161b22;
        border: round #38bdf8;
        padding: 1 2;
    }
    #clip-header {
        color: #38bdf8;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    #clip-filter-inp {
        height: 3;
        background: #0d1117;
        border: round #30363d;
        color: #f0f6fc;
        margin-bottom: 1;
    }
    #clip-entries {
        height: 1fr;
        background: #0d1117;
        border: round #21262d;
    }
    #clip-actions {
        height: 3;
        margin-top: 1;
        align: right middle;
    }
    #btn-clip-select {
        background: #238636;
        color: #ffffff;
        border: none;
        margin-right: 1;
    }
    #btn-clip-dismiss {
        background: #21262d;
        color: #c9d1d9;
        border: none;
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
        with Vertical(id="clip-box"):
            yield Label("📋  Clipboard History", id="clip-header")
            yield Input(placeholder="Search clipboard...", id="clip-filter-inp")
            yield OptionList(id="clip-entries")
            with Horizontal(id="clip-actions"):
                yield Button("Copy Selected", id="btn-clip-select")
                yield Button("Close", id="btn-clip-dismiss")

    def on_mount(self):
        self.load_history()

    def load_history(self, query: str = ""):
        try:
            if HYPR_AVAILABLE:
                self.raw_items = WaylandPeripherals.get_clipboard_history(30)
            else:
                self.raw_items = ["Clipboard provider not available"]
        except Exception as e:
            self.raw_items = [f"Error: {e}"]

        opt_list = self.query_one("#clip-entries", OptionList)
        opt_list.clear_options()
        filtered = [it for it in self.raw_items if query.lower() in it.lower()] if query else self.raw_items
        for item in filtered:
            clean_item = item.strip().replace("\n", " ")[:60]
            opt_list.add_option(Option(prompt=clean_item, id=clean_item))

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "clip-filter-inp":
            self.load_history(event.value)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-clip-select":
            self.copy_selected()
        self.dismiss()

    def action_copy_selected(self):
        self.copy_selected()
        self.dismiss()

    def action_close(self):
        self.dismiss()

    def copy_selected(self):
        try:
            opt_list = self.query_one("#clip-entries", OptionList)
            if opt_list.highlighted is not None:
                opt = opt_list.get_option_at_index(opt_list.highlighted)
                val = str(opt.prompt)
                if HYPR_AVAILABLE:
                    WaylandPeripherals.paste_from_history(val)
                if hasattr(self.app, "_log"):
                    self.app._log(f"📋 Copied to clipboard: '{val[:35]}...'")
        except Exception as e:
            if hasattr(self.app, "_log"):
                self.app._log(f"⚠️ Clipboard error: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# AUDIO WAVEFORM WIDGET
# ═════════════════════════════════════════════════════════════════════════════

class TUIWaveformWidget(Static):
    """Subtle, modern animated audio waveform"""
    state: reactive[str] = reactive("idle")
    phase: float = 0.0

    BAR_CHARS = [" ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]

    def on_mount(self):
        self.set_interval(0.08, self.tick)

    def set_state(self, new_state: str):
        self.state = new_state.lower()

    def tick(self):
        self.phase += 0.25
        num_bars = 16
        bars = []

        if self.state == "listening":
            color = "#38bdf8"
            tag = "Listening"
            for i in range(num_bars):
                v = math.sin(self.phase + i * 0.5) * math.cos(self.phase * 0.4 + i * 0.25)
                level = int(round((v + 1.0) / 2.0 * (len(self.BAR_CHARS) - 1)))
                bars.append(self.BAR_CHARS[max(0, min(len(self.BAR_CHARS) - 1, level))])
        elif self.state == "thinking":
            color = "#a78bfa"
            tag = "Thinking"
            for i in range(num_bars):
                v = (math.sin(self.phase + i * 0.35) + math.sin(self.phase * 1.2 - i * 0.4)) / 2.0
                level = int(round((v + 1.0) / 2.0 * (len(self.BAR_CHARS) - 1)))
                bars.append(self.BAR_CHARS[max(0, min(len(self.BAR_CHARS) - 1, level))])
        elif self.state == "recording":
            color = "#f85149"
            tag = "Recording"
            for i in range(num_bars):
                v = abs(math.sin(self.phase * 1.5 + i * 0.7))
                level = int(round(v * (len(self.BAR_CHARS) - 1)))
                bars.append(self.BAR_CHARS[max(0, min(len(self.BAR_CHARS) - 1, level))])
        else:  # idle
            color = "#8b949e"
            tag = "Ready"
            for i in range(num_bars):
                v = math.sin(self.phase * 0.3 + i * 0.2) * 0.25
                level = int(round((v + 0.25) / 1.0 * 2))
                bars.append(self.BAR_CHARS[max(0, min(len(self.BAR_CHARS) - 1, level))])

        bar_str = "".join(bars)
        self.update(f"[{color}]{bar_str}[/{color}] [dim {color}]{tag}[/dim {color}]")


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR: SYSTEM TELEMETRY & DESKTOP CONTROLS
# ═════════════════════════════════════════════════════════════════════════════

class SidebarPanel(Static):
    """Clean, unified modern sidebar showing Telemetry, Hyprland & Hardware"""

    def on_mount(self):
        self.refresh_all()
        self.set_interval(2.0, self.refresh_all)

    def _meter(self, pct: float, color: str, width: int = 12) -> str:
        pct = max(0, min(100, pct))
        filled = int(round(pct / 100 * width))
        empty = width - filled
        return f"[{color}]{'■' * filled}[/{color}][dim #30363d]{'□' * empty}[/dim #30363d] [{color}]{pct:>3.0f}%[/{color}]"

    def refresh_all(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            bat = psutil.sensors_battery()
            now = datetime.now()

            # Net rate
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

            cpu_col = "#2dd4bf" if cpu < 65 else ("#e3b341" if cpu < 85 else "#f85149")
            mem_col = "#38bdf8" if mem.percent < 75 else ("#e3b341" if mem.percent < 90 else "#f85149")
            disk_col = "#a78bfa" if disk.percent < 80 else "#f85149"

            bat_pct = bat.percent if bat else 100
            bat_status = "⚡ Plugged" if (bat and bat.power_plugged) else "🔋 Battery"

            # Hyprland Status
            hypr_ws_str = "Standby"
            win_title = "Desktop"
            win_class = ""
            if HYPR_AVAILABLE:
                try:
                    active_ws = WorkspaceManager.get_active_workspace_id()
                    workspaces = WorkspaceManager.get_all_workspaces()
                    occupied = {w.get("id"): w.get("windows", 0) for w in workspaces}

                    badges = []
                    for i in range(1, 6):
                        if i == active_ws:
                            badges.append(f"[bold #ffffff on #238636] {i} [/bold #ffffff on #238636]")
                        elif i in occupied:
                            badges.append(f"[#38bdf8]●{i}[/#38bdf8]")
                        else:
                            badges.append(f"[dim #8b949e]{i}[/dim #8b949e]")
                    hypr_ws_str = " ".join(badges)

                    aw = WindowManager.get_active_window()
                    if aw:
                        win_title = aw.get("title", "Desktop")[:22]
                        win_class = aw.get("class", "")[:12]
                except Exception:
                    pass

            # Power Profile
            power_prof = "balanced"
            if LAPTOP_AVAILABLE:
                try:
                    raw_prof = PowerManager.get_power_profile()
                    if "power-saver" in raw_prof or "powersave" in raw_prof:
                        power_prof = "power-saver"
                    elif "performance" in raw_prof:
                        power_prof = "performance"
                    else:
                        power_prof = "balanced"
                except Exception:
                    pass

            p_saver = "[#2dd4bf]Saver[/]" if power_prof == "power-saver" else "[dim]Saver[/]"
            p_bal = "[#38bdf8]Balanced[/]" if power_prof == "balanced" else "[dim]Bal[/]"
            p_perf = "[#e3b341]Perf[/]" if power_prof == "performance" else "[dim]Perf[/]"

            text = (
                f"[bold #e6edf3]SYSTEM TELEMETRY[/bold #e6edf3]\n"
                f"[dim]CPU[/dim]  {self._meter(cpu, cpu_col)}{temp_str}\n"
                f"[dim]RAM[/dim]  {self._meter(mem.percent, mem_col)} [dim]{mem.used/1e9:.1f}G[/dim]\n"
                f"[dim]DSK[/dim]  {self._meter(disk.percent, disk_col)}\n"
                f"[dim]NET[/dim]  [#a78bfa]{kbps:>5.1f} KB/s[/]\n"
                f"[dim]BAT[/dim]  {self._meter(bat_pct, '#2dd4bf')} [dim]{bat_status}[/dim]\n"
                f"\n"
                f"[bold #e6edf3]HYPRLAND DESKTOP[/bold #e6edf3]\n"
                f"Workspaces: {hypr_ws_str}\n"
                f"Window: [bold white]{win_title}[/bold white] [dim]({win_class})[/dim]\n"
                f"\n"
                f"[bold #e6edf3]POWER PROFILE[/bold #e6edf3]\n"
                f"{p_saver} · {p_bal} · {p_perf}\n"
            )
            self.update(text)
        except Exception as e:
            self.update(f"[red]Sidebar update: {e}[/red]")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN BENX TUI APPLICATION
# ═════════════════════════════════════════════════════════════════════════════

class BenXTUI(App):
    """Clean, modern minimalist BenX Terminal Assistant"""
    TITLE = "BenX Assistant v2.0"

    CSS = """
    Screen {
        background: #0d1117;
        color: #c9d1d9;
    }

    /* ── Top Header ── */
    #header-bar {
        height: 3;
        background: #161b22;
        border-bottom: solid #21262d;
        padding: 0 2;
        align: left middle;
    }
    #logo-title {
        color: #38bdf8;
        text-style: bold;
        margin-right: 1;
    }
    #status-pill {
        color: #2dd4bf;
        margin-right: 2;
    }
    #top-model-display {
        color: #a78bfa;
        width: 1fr;
    }
    TUIWaveformWidget {
        width: 28;
        content-align: right middle;
        margin-right: 2;
    }
    #btn-settings-top {
        background: #21262d;
        color: #c9d1d9;
        border: none;
        height: 3;
        padding: 0 1;
    }
    #btn-settings-top:hover {
        background: #30363d;
        color: #ffffff;
    }

    /* ── Main Layout ── */
    #body-container {
        height: 1fr;
    }

    /* ── Sidebar (Left) ── */
    #sidebar {
        width: 32;
        background: #11161d;
        border-right: solid #21262d;
        padding: 1 1;
    }
    SidebarPanel {
        height: auto;
        margin-bottom: 1;
    }

    .side-btn-row {
        height: 3;
        margin-bottom: 1;
    }
    .side-btn {
        min-width: 7;
        background: #161b22;
        color: #8b949e;
        border: none;
        margin-right: 1;
        padding: 0 1;
    }
    .side-btn:hover {
        background: #21262d;
        color: #38bdf8;
    }

    /* ── Chat Container (Right/Center) ── */
    #main-chat-area {
        width: 1fr;
        background: #0d1117;
        padding: 1 2;
    }

    #chat-log {
        height: 1fr;
        background: #0d1117;
        border: round #21262d;
        padding: 1 1;
    }

    /* Quick Action Chips */
    #quick-chips-bar {
        height: 3;
        margin-top: 1;
    }
    .chip-btn {
        background: #161b22;
        color: #8b949e;
        border: none;
        margin-right: 1;
        padding: 0 1;
    }
    .chip-btn:hover {
        background: #21262d;
        color: #2dd4bf;
    }

    /* Input Composer */
    #composer-bar {
        height: 3;
        margin-top: 1;
    }
    #btn-screen-attach {
        width: 4;
        background: #21262d;
        color: #38bdf8;
        border: none;
        margin-right: 1;
    }
    #btn-screen-attach:hover {
        background: #30363d;
    }
    #chat-input-box {
        width: 1fr;
        background: #161b22;
        border: round #30363d;
        color: #f0f6fc;
        padding: 0 1;
    }
    #chat-input-box:focus {
        border: round #38bdf8;
    }
    #btn-chat-send {
        width: 6;
        background: #238636;
        color: #ffffff;
        border: none;
        margin-left: 1;
    }
    #btn-chat-send:hover {
        background: #2ea043;
    }

    /* ── Bottom Status Bar ── */
    #footer-status-bar {
        height: 1;
        background: #161b22;
        border-top: solid #21262d;
        color: #8b949e;
        padding: 0 2;
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
                self.call_from_thread(self._log, "AI Engine ready.")
            except RuntimeError:
                pass
        except Exception as e:
            try:
                self.call_from_thread(self._log, f"Engine note: {e}")
            except RuntimeError:
                pass

    def compose(self) -> ComposeResult:
        # Header Top Bar
        with Horizontal(id="header-bar"):
            yield Label("BenX", id="logo-title")
            yield Label("● Online", id="status-pill")
            yield Label("[Auto Router]", id="top-model-display")
            yield TUIWaveformWidget(id="header-waveform")
            yield Button("⚙️ Settings (F6)", id="btn-settings-top")

        with Horizontal(id="body-container"):
            # ── Sidebar (Left) ────────────────────────────────────────────────
            with Vertical(id="sidebar"):
                yield SidebarPanel(id="sidebar-panel")

                # Clean Desktop Controls
                yield Label("[bold #e6edf3]WINDOW ACTIONS[/bold #e6edf3]")
                with Horizontal(classes="side-btn-row"):
                    yield Button("🪟 Float", id="act-float", classes="side-btn")
                    yield Button("📌 Pin", id="act-pin", classes="side-btn")
                    yield Button("🔲 Full", id="act-full", classes="side-btn")
                with Horizontal(classes="side-btn-row"):
                    yield Button("◀ Move", id="act-move-l", classes="side-btn")
                    yield Button("Move ▶", id="act-move-r", classes="side-btn")
                    yield Button("✕ Close", id="act-close", classes="side-btn")

                # Hardware Controls
                yield Label("[bold #e6edf3]HARDWARE ACTIONS[/bold #e6edf3]")
                with Horizontal(classes="side-btn-row"):
                    yield Button("🌱 Saver", id="act-saver", classes="side-btn")
                    yield Button("⚖️ Bal", id="act-bal", classes="side-btn")
                    yield Button("⚡ Perf", id="act-perf", classes="side-btn")
                with Horizontal(classes="side-btn-row"):
                    yield Button("🔒 Lock", id="act-lock", classes="side-btn")
                    yield Button("📋 Clip", id="act-clip", classes="side-btn")
                    yield Button("🛑 Off", id="act-off", classes="side-btn")

            # ── Main Conversation Node (Right) ────────────────────────────────
            with Vertical(id="main-chat-area"):
                yield RichLog(id="chat-log", highlight=True, markup=True)

                # Quick Action Chips
                with Horizontal(id="quick-chips-bar"):
                    for idx, (lbl, _) in enumerate(QUICK_ACTIONS[:5]):
                        yield Button(lbl, classes="chip-btn", id=f"chip-{idx}")

                # Composer
                with Horizontal(id="composer-bar"):
                    yield Button("📷", id="btn-screen-attach", tooltip="Attach screenshot")
                    yield Input(placeholder="Ask BenX or type an automation command (e.g. /help)...", id="chat-input-box")
                    yield Button("Send", id="btn-chat-send")

        # Footer Status Line
        yield Label(
            "● Ready  │  Enter: Send  │  F1: Help  │  F2: Agent  │  F3: Voice  │  F4: Screenshot  │  F6: Settings  │  Ctrl+C: Quit",
            id="footer-status-bar"
        )

    def on_mount(self):
        chat = self.query_one("#chat-log", RichLog)
        ts = datetime.now().strftime("%H:%M")
        chat.write(
            f"[dim #8b949e]{ts}[/dim #8b949e] [bold #38bdf8]BenX Assistant v2.0[/bold #38bdf8]\n"
            f"[dim #c9d1d9]Welcome to BenX. Running natively on Arch Linux + Hyprland (Wayland).\n"
            f"You can control windows, automate apps, manage power, or chat naturally with AI.[/dim #c9d1d9]\n"
        )
        self.query_one("#chat-input-box", Input).focus()
        threading.Thread(target=self._init_ai_engine, daemon=True).start()

    # ── Button Handlers ───────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if not bid:
            return

        if bid == "btn-settings-top":
            self.action_open_settings()
        elif bid == "btn-chat-send":
            inp = self.query_one("#chat-input-box", Input)
            val = inp.value.strip()
            inp.value = ""
            if val:
                self.send_user_message(val)
        elif bid == "btn-screen-attach":
            self.action_take_screen()
        elif bid.startswith("chip-"):
            try:
                idx = int(bid.replace("chip-", ""))
                _, cmd = QUICK_ACTIONS[idx]
                inp = self.query_one("#chat-input-box", Input)
                inp.value = cmd
                inp.focus()
            except Exception:
                pass

        # Window Actions
        elif bid == "act-float":
            if HYPR_AVAILABLE:
                WindowManager.toggle_floating()
                self._log("Toggled active window float.")
                self.action_refresh_state()
        elif bid == "act-pin":
            if HYPR_AVAILABLE:
                WindowManager.toggle_pin()
                self._log("Toggled active window pin.")
                self.action_refresh_state()
        elif bid == "act-full":
            if HYPR_AVAILABLE:
                WindowManager.fullscreen()
                self._log("Toggled fullscreen.")
                self.action_refresh_state()
        elif bid == "act-move-l":
            if HYPR_AVAILABLE:
                WindowManager.move_active("l")
                self._log("Moved active window left.")
        elif bid == "act-move-r":
            if HYPR_AVAILABLE:
                WindowManager.move_active("r")
                self._log("Moved active window right.")
        elif bid == "act-close":
            if HYPR_AVAILABLE:
                WindowManager.close_active()
                self._log("Closed active window.")
                self.action_refresh_state()

        # Power & Hardware Actions
        elif bid == "act-saver":
            self.set_power_profile("power-saver")
        elif bid == "act-bal":
            self.set_power_profile("balanced")
        elif bid == "act-perf":
            self.set_power_profile("performance")
        elif bid == "act-lock":
            self.action_lock_screen()
        elif bid == "act-clip":
            self.push_screen(ClipboardModal())
        elif bid == "act-off":
            self.confirm_and_run(
                "Shutdown System?",
                "Are you sure you want to turn off the computer?",
                lambda: PowerManager.shutdown() if LAPTOP_AVAILABLE else None
            )

    def set_power_profile(self, profile: str):
        if LAPTOP_AVAILABLE:
            res = PowerManager.set_power_profile(profile)
            self._log(f"Power profile: {res}")
            self.action_refresh_state()

    def confirm_and_run(self, title: str, message: str, action_func):
        def on_result(confirmed: bool):
            if confirmed:
                self._log(f"Executing: {title}")
                try:
                    action_func()
                except Exception as e:
                    self._log(f"Error: {e}")

        self.push_screen(TUIConfirmModal(title, message), on_result)

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "chat-input-box":
            val = event.value.strip()
            event.input.value = ""
            if val:
                self.send_user_message(val)

    # ── Message Processing ────────────────────────────────────────────────────

    def send_user_message(self, text: str):
        if not text and not self.pending_image:
            return

        chat = self.query_one("#chat-log", RichLog)
        ts = datetime.now().strftime("%H:%M")
        img_badge = f" [bold #38bdf8][📷 {os.path.basename(self.pending_image)}][/bold #38bdf8]" if self.pending_image else ""
        chat.write(f"\n[dim #8b949e]{ts}[/dim #8b949e] [bold #38bdf8]You:[/bold #38bdf8] {text}{img_badge}")

        self._set_status("BenX is thinking...")
        self.set_waveform_state("thinking")

        self.execute_task_worker(text, self.pending_image)
        self.pending_image = None

    @work(thread=True)
    def execute_task_worker(self, text: str, image_path: Optional[str] = None):
        chat = self.query_one("#chat-log", RichLog)
        try:
            if not self.ai_engine:
                from jarvis_ai.ai_engine import AIEngine
                self.ai_engine = AIEngine()

            def on_agent_step(step_text: str):
                self.app.call_from_thread(self._log, f"Step: {step_text[:65]}")

            if image_path:
                response = self.ai_engine.chat(text, image_path=image_path)
            elif self.agent_mode:
                response = self.ai_engine.agent_run(text, on_step_cb=on_agent_step)
                if not response:
                    response = self.ai_engine.chat(text)
            else:
                from jarvis_ai.executor import CommandExecutor
                cmd_json = self.ai_engine.interpret_command(
                    text,
                    conversation_context=self.ai_engine.conversation_history,
                    learning_engine=self.ai_engine.learning_engine,
                )
                response = CommandExecutor.execute(cmd_json, self.ai_engine, text)
                if response is None:
                    response = self.ai_engine.chat(text)

            ts = datetime.now().strftime("%H:%M")
            self.app.call_from_thread(
                chat.write,
                f"[dim #8b949e]{ts}[/dim #8b949e] [bold #2dd4bf]BenX:[/bold #2dd4bf]\n{response}\n"
            )
            self.app.call_from_thread(self._set_status, "Ready")
            self.app.call_from_thread(self.set_waveform_state, "idle")
            self.app.call_from_thread(self.action_refresh_state)
        except Exception as err:
            ts = datetime.now().strftime("%H:%M")
            self.app.call_from_thread(chat.write, f"[dim #8b949e]{ts}[/dim #8b949e] [bold #f85149]Error:[/bold #f85149] {err}")
            self.app.call_from_thread(self._set_status, "Error")
            self.app.call_from_thread(self.set_waveform_state, "idle")

    # ── Actions & Hotkeys ─────────────────────────────────────────────────────

    def action_clear_chat(self):
        self.query_one("#chat-log", RichLog).clear()
        self._set_status("Chat cleared")

    def action_toggle_agent(self):
        self.agent_mode = not self.agent_mode
        state_str = "Agent: ON" if self.agent_mode else "Agent: OFF"
        self._log(f"Mode changed: {state_str}")
        self._set_status(state_str)

    def action_open_settings(self):
        self.push_screen(TUISettingsModal())

    def action_refresh_state(self):
        try:
            sp = self.query_one("#sidebar-panel", SidebarPanel)
            sp.refresh_all()
        except Exception:
            pass

    def action_take_screen(self):
        try:
            if HYPR_AVAILABLE:
                path = WaylandPeripherals.take_screenshot(select_region=False)
            else:
                from jarvis_ai.command_engine import CommandEngine
                path = CommandEngine.take_screenshot()

            if path and os.path.exists(path):
                self.pending_image = path
                inp = self.query_one("#chat-input-box", Input)
                inp.value = "analyze this screenshot"
                inp.focus()
                self._set_status(f"Screenshot attached: {os.path.basename(path)}")
        except Exception as e:
            self._log(f"Screenshot error: {e}")

    def action_lock_screen(self):
        if LAPTOP_AVAILABLE:
            PowerManager.lock()
            self._log("Screen locked.")

    def action_voice_input(self):
        self._set_status("Listening...")
        self.set_waveform_state("listening")
        self.listen_voice_worker()

    @work(thread=True)
    def listen_voice_worker(self):
        try:
            from jarvis_ai.voice_handler import VoiceHandler
            vh = VoiceHandler()
            text = vh.listen()
            if text:
                self.app.call_from_thread(self.send_user_message, text)
            else:
                self.app.call_from_thread(self._set_status, "No voice input detected")
                self.app.call_from_thread(self.set_waveform_state, "idle")
        except Exception as exc:
            self.app.call_from_thread(self._set_status, f"Voice error: {exc}")
            self.app.call_from_thread(self.set_waveform_state, "idle")

    def action_show_help(self):
        chat = self.query_one("#chat-log", RichLog)
        chat.write(
            "\n[bold #38bdf8]── BenX Assistant Hotkeys & Commands ──[/bold #38bdf8]\n"
            "  [bold white]Enter[/bold white]       Send message / execute command\n"
            "  [bold white]F1[/bold white]          Show this help guide\n"
            "  [bold white]F2[/bold white]          Toggle Autonomous ReAct Agent\n"
            "  [bold white]F3[/bold white]          Voice Input (Speech-to-Text)\n"
            "  [bold white]F4[/bold white]          Screenshot Desktop for Vision OCR\n"
            "  [bold white]F5[/bold white]          Refresh Telemetry & Workspaces\n"
            "  [bold white]F6[/bold white]          Open Settings & Preferences\n"
            "  [bold white]F8[/bold white]          Lock Desktop (hyprlock)\n"
            "  [bold white]Ctrl+L[/bold white]      Clear chat log\n"
            "  [bold white]Ctrl+C[/bold white]      Quit BenX\n"
            "[dim #8b949e]Quick commands: 'open chrome', 'switch to workspace 2', 'set power-saver', 'top cpu processes'[/dim #8b949e]\n"
        )

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def set_waveform_state(self, state: str):
        try:
            wf = self.query_one("#header-waveform", TUIWaveformWidget)
            wf.set_state(state)
        except Exception:
            pass

    def _log(self, msg: str):
        try:
            self._set_status(msg)
        except Exception:
            pass

    def _set_status(self, status: str):
        try:
            lbl = self.query_one("#footer-status-bar", Label)
            lbl.update(f"● {status}  │  Enter: Send  │  F1: Help  │  F2: Agent  │  F4: Screenshot  │  F6: Settings  │  Ctrl+C: Quit")
        except Exception:
            pass


if __name__ == "__main__":
    BenXTUI().run()

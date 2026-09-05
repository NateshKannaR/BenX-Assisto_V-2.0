#!/usr/bin/env python3
"""
BenX TUI — Ultimate Terminal User Interface
Matches GTK4 feature set: 3-panel glassmorphic cyberpunk layout, live telemetry,
workspace window state, animated core logo, OpenRouter & Groq model selector,
autonomous ReAct agent streaming, quick action automation chips, and voice sensing.
"""
import sys, os, time, math, threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

import psutil
from rich.text import Text
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static, Label, Select, Switch, Button
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.binding import Binding
from textual.reactive import reactive
from textual import work

# ── Load Config & Models ──────────────────────────────────────────────────────
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
        "llama-3.1-8b-instant"
    ]

QUICK_ACTIONS = [
    ("👁️ Screen OCR",  "analyze my screen and describe what you see"),
    ("⚡ Automate",    "automate opening chrome and going to github.com"),
    ("⌨️ WS Type",     "in workspace 1 type ls -la"),
    ("📱 Mobile ADB",  "check connected mobile phone and list UI elements"),
    ("🔍 Scan Code",   "scan my project for issues"),
    ("📊 Telemetry",   "system info"),
]

# ── Animated Cyberpunk Core Logo ──────────────────────────────────────────────
LOGO_FRAMES = [
    """[bold #60ffb9]  ╭─── ◈ ─ B E N X  A S S I S T O ─ ◈ ───╮[/bold #60ffb9]
[bold #61d8ff]  │  ░▒▓█   Adaptive Linux Node   █▓▒░  │[/bold #61d8ff]
[bold #8eb5ac]  │       ● ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ●     │[/bold #8eb5ac]
[bold #60ffb9]  ╰─────────────────────────────────────╯[/bold #60ffb9]""",

    """[bold #61d8ff]  ╭─── ◈ ─ B E N X  A S S I S T O ─ ◈ ───╮[/bold #61d8ff]
[bold #60ffb9]  │  ▒▓██   ReAct Agent Active    ██▓▒  │[/bold #60ffb9]
[bold #8eb5ac]  │       ─ ● ─ ─ ─ ─ ─ ─ ─ ─ ─ ● ─     │[/bold #8eb5ac]
[bold #61d8ff]  ╰─────────────────────────────────────╯[/bold #61d8ff]""",

    """[bold #60ffb9]  ╭─── ◈ ─ B E N X  A S S I S T O ─ ◈ ───╮[/bold #60ffb9]
[bold #61d8ff]  │  ▓███   Neural Core Synced    ███▓  │[/bold #61d8ff]
[bold #8eb5ac]  │       ─ ─ ● ─ ─ ─ ─ ─ ─ ─ ● ─ ─     │[/bold #8eb5ac]
[bold #60ffb9]  ╰─────────────────────────────────────╯[/bold #60ffb9]""",

    """[bold #61d8ff]  ╭─── ◈ ─ B E N X  A S S I S T O ─ ◈ ───╮[/bold #61d8ff]
[bold #60ffb9]  │  ████   Autonomous Stack Ready  ████│[/bold #60ffb9]
[bold #8eb5ac]  │       ─ ─ ─ ● ─ ─ ─ ─ ─ ● ─ ─ ─     │[/bold #8eb5ac]
[bold #61d8ff]  ╰─────────────────────────────────────╯[/bold #61d8ff]""",
]


class AnimatedLogo(Static):
    """Pulsing cyberpunk core logo"""
    frame = reactive(0)

    def on_mount(self):
        self.set_interval(0.6, self.next_frame)

    def next_frame(self):
        self.frame = (self.frame + 1) % len(LOGO_FRAMES)

    def watch_frame(self, frame: int):
        self.update(LOGO_FRAMES[frame])


# ── Telemetry & Diagnostics Panel (Left) ───────────────────────────────────────
class StatsPanel(Static):
    """Real-time Linux system telemetry matching GTK4 stat cards"""

    def on_mount(self):
        self.update_stats()
        self.set_interval(1.5, self.update_stats)

    def _meter(self, pct: float, color: str, w: int = 16) -> str:
        pct = max(0, min(100, pct))
        filled = int(round(pct / 100 * w))
        empty = w - filled
        return f"[{color}]{'█' * filled}[/{color}][dim #1a3a2a]{'░' * empty}[/dim #1a3a2a] [bold {color}]{pct:>3.0f}%[/bold {color}]"

    def update_stats(self):
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            net = psutil.net_io_counters()
            bat = psutil.sensors_battery()
            now = datetime.now()

            # Network Throughput calculation
            now_bytes = net.bytes_sent + net.bytes_recv
            prev = getattr(self, "_prev_net", (now_bytes, now.timestamp()))
            delta_bytes = max(0, now_bytes - prev[0])
            delta_t = max(now.timestamp() - prev[1], 0.1)
            kbps = delta_bytes / delta_t / 1024
            self._prev_net = (now_bytes, now.timestamp())

            # CPU Temperature detection
            temp_str = ""
            try:
                temps = psutil.sensors_temperatures()
                for lst in temps.values():
                    if lst and lst[0].current > 0:
                        temp_str = f" {lst[0].current:.0f}°C"
                        break
            except Exception:
                pass

            # Color styling based on thresholds
            cpu_color = "#60ffb9" if cpu < 65 else ("#ffc857" if cpu < 85 else "#ff6b6b")
            mem_color = "#61d8ff" if mem.percent < 75 else ("#ffc857" if mem.percent < 90 else "#ff6b6b")
            disk_color = "#b794ff" if disk.percent < 80 else "#ff6b6b"

            bat_str = f"{bat.percent:.0f}% {'⚡ Plugged' if bat.power_plugged else '🔋 Battery'}" if bat else "AC Line"
            bat_pct = bat.percent if bat else 100

            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            uptime_str = f"{int(uptime.total_seconds() // 3600)}h {int((uptime.total_seconds() % 3600) // 60)}m"

            text = (
                f"[bold #61d8ff]🕒 {now.strftime('%H:%M:%S')}[/bold #61d8ff]  [dim #8eb5ac]{now.strftime('%b %d, %Y')}[/dim #8eb5ac]\n"
                f"[dim #1a3a2a]{'━' * 23}[/dim #1a3a2a]\n\n"
                f"[bold #8eb5ac]🌐 NETWORK I/O[/bold #8eb5ac] [bold #b794ff]{kbps:>5.1f} KB/s[/bold #b794ff]\n"
                f"{self._meter(min(kbps / 400 * 100, 100), '#b794ff')}\n\n"
                f"[bold #8eb5ac]⚡ CPU USAGE[/bold #8eb5ac] [{cpu_color}]{cpu:>3.0f}%{temp_str}[/{cpu_color}]\n"
                f"{self._meter(cpu, cpu_color)}\n\n"
                f"[bold #8eb5ac]💾 MEMORY RAM[/bold #8eb5ac] [{mem_color}]{mem.used / 1e9:.1f}/{mem.total / 1e9:.1f}GB[/{mem_color}]\n"
                f"{self._meter(mem.percent, mem_color)}\n\n"
                f"[bold #8eb5ac]📁 ROOT DISK[/bold #8eb5ac] [{disk_color}]{disk.used / 1e9:.0f}/{disk.total / 1e9:.0f}GB[/{disk_color}]\n"
                f"{self._meter(disk.percent, disk_color)}\n\n"
                f"[bold #8eb5ac]🔋 POWER STATE[/bold #8eb5ac] [green]{bat_str}[/green]\n"
                f"{self._meter(bat_pct, '#60ffb9')}\n\n"
                f"[dim #1a3a2a]{'━' * 23}[/dim #1a3a2a]\n"
                f"[dim #8eb5ac]OS: [/dim #8eb5ac][bold white]Arch Linux[/bold white]\n"
                f"[dim #8eb5ac]WM: [/dim #8eb5ac][bold white]Hyprland (Wayland)[/bold white]\n"
                f"[dim #8eb5ac]UP: [/dim #8eb5ac][bold white]{uptime_str}[/bold white]\n"
            )
            self.update(text)
        except Exception as e:
            self.update(f"[red]Telemetry error: {e}[/red]")


# ── Workspace Monitor Widget (Center) ──────────────────────────────────────────
class WorkspaceWidget(Static):
    """Hyprland workspace awareness widget matching GTK monitor"""

    def on_mount(self):
        self.update_ws()
        self.set_interval(4.0, self.update_ws)

    def update_ws(self):
        try:
            from jarvis_ai.workspace_monitor import WorkspaceMonitor
            summary = WorkspaceMonitor.state_summary()
            if not summary or "Error" in summary:
                summary = "Active Desktop: Wayland Session\nFocus: BenX Terminal Interface"
            lines = summary.split("\n")[:4]
            self.update(
                f"[bold #61d8ff]◈ DESKTOP WORKSPACE MAP[/bold #61d8ff]\n"
                + "\n".join(f"[dim #8eb5ac]▪[/dim #8eb5ac] [white]{l}[/white]" for l in lines if l.strip())
            )
        except Exception:
            self.update("[dim #8eb5ac]Desktop monitor: Ready (Hyprland / Wayland)[/dim #8eb5ac]")


# ── Main BenX TUI Application ─────────────────────────────────────────────────
class BenXTUI(App):
    """Full-featured GTK4-parity Textual UI for BenX AI Assistant"""
    TITLE = "BenX AI Assistant v2.0"

    CSS = """
    Screen {
        background: #020406;
        color: #eafaf1;
    }

    /* ── Top Bar ── */
    #topbar {
        height: 3;
        background: #040d12;
        border-bottom: solid #143626;
        padding: 0 2;
        align: left middle;
    }
    #top-pill {
        color: #60ffb9;
        text-style: bold;
        margin-right: 2;
    }
    #top-title {
        color: #f4fff9;
        text-style: bold;
        width: 1fr;
    }
    #top-model-tag {
        color: #61d8ff;
        text-style: bold;
        margin-right: 2;
    }

    /* ── 3-Panel Main Grid ── */
    #main-grid {
        height: 1fr;
    }

    #left-panel {
        width: 27;
        border-right: solid #143626;
        background: #03080d;
        padding: 1 1;
    }

    #center-panel {
        width: 1fr;
        border-right: solid #143626;
        background: #03070b;
        padding: 1 1;
    }

    #right-panel {
        width: 48;
        background: #04090e;
        padding: 1 1;
    }

    /* Panel Headers */
    .panel-title {
        color: #60ffb9;
        text-style: bold;
        margin-bottom: 0;
    }
    .panel-sub {
        color: #8eb5ac;
        text-style: dim;
        margin-bottom: 1;
    }

    /* Center Content */
    AnimatedLogo {
        height: 6;
        content-align: center middle;
        border: solid #143626;
        background: #020407;
        margin-bottom: 1;
    }

    WorkspaceWidget {
        height: 6;
        border: solid #143626;
        background: #020509;
        padding: 0 1;
        margin-bottom: 1;
    }

    #activity-stream {
        height: 1fr;
        border: solid #143626;
        background: #010305;
        padding: 0 1;
    }

    /* Right Panel (Chat Node) */
    #controls-bar {
        height: 3;
        margin-bottom: 1;
        align: left middle;
    }
    #model-label {
        width: 7;
        color: #8eb5ac;
        content-align: left middle;
    }
    #model-select {
        width: 28;
        background: #030a0f;
        border: solid #143626;
        color: #60ffb9;
    }
    #agent-label {
        width: 7;
        color: #8eb5ac;
        content-align: left middle;
        margin-left: 1;
    }
    #agent-switch {
        width: 6;
    }

    #chat-window {
        height: 1fr;
        border: solid #143626;
        background: #010305;
        padding: 0 1;
    }

    /* Quick Action Chips */
    #chips-container {
        height: 3;
        margin-top: 1;
    }
    .quick-chip {
        width: 1fr;
        background: #040d12;
        border: solid #143626;
        color: #8eb5ac;
        min-width: 0;
        padding: 0 1;
    }
    .quick-chip:hover {
        background: #0c2b1e;
        border: solid #60ffb9;
        color: #60ffb9;
    }
    .quick-chip:focus {
        background: #0c2b1e;
        border: solid #60ffb9;
        color: #60ffb9;
    }

    /* Composer */
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
    #attach-btn:hover {
        background: #09202a;
        border: solid #61d8ff;
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
    #send-btn:hover {
        background: #15573a;
    }

    /* Bottom Bar */
    #status-footer {
        height: 1;
        background: #04120c;
        color: #60ffb9;
        padding: 0 2;
    }

    Select > SelectCurrent {
        background: #030a0f;
        color: #60ffb9;
        border: solid #143626;
    }
    Select:focus > SelectCurrent {
        border: solid #60ffb9;
    }
    Switch {
        margin: 0 1;
    }
    Footer {
        background: #03080d;
        color: #8eb5ac;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit",         "Quit"),
        Binding("ctrl+l", "clear_chat",   "Clear Chat"),
        Binding("f1",     "show_help",    "Help"),
        Binding("f2",     "toggle_agent", "Agent Mode"),
        Binding("f3",     "voice_input",  "Voice"),
        Binding("f4",     "take_screen",  "Screenshot"),
    ]

    agent_mode = reactive(False)

    def __init__(self):
        super().__init__()
        self.ai_engine = None
        self.pending_image = None

    def _init_ai_engine(self):
        try:
            from jarvis_ai.ai_engine import AIEngine
            self.ai_engine = AIEngine()
            self.call_from_thread(self._log_mission, "✅ AI Engine & OpenRouter stack online")
        except Exception as e:
            self.call_from_thread(self._log_mission, f"⚠️ Engine init: {e}")

    def compose(self) -> ComposeResult:
        # Top bar
        with Horizontal(id="topbar"):
            yield Label("● BENX", id="top-pill")
            yield Label("Adaptive Linux Control & Automation Platform", id="top-title")
            yield Label("[OpenRouter]", id="top-model-tag")

        with Horizontal(id="main-grid"):
            # ── LEFT: Telemetry & Diagnostics ──────────────────────────────────
            with Vertical(id="left-panel"):
                yield Label("◈ DIAGNOSTICS", classes="panel-title")
                yield Label("Hardware & Telemetry", classes="panel-sub")
                yield StatsPanel()

            # ── CENTER: Hero Core, Workspace & Mission Stream ─────────────────
            with Vertical(id="center-panel"):
                yield AnimatedLogo(LOGO_FRAMES[0])
                yield WorkspaceWidget()
                yield Label("◈ MISSION STREAM", classes="panel-title")
                yield Label("Real-time task & event pipeline", classes="panel-sub")
                yield RichLog(id="activity-stream", highlight=True, markup=True)

            # ── RIGHT: Assistant Chat Node ────────────────────────────────────
            with Vertical(id="right-panel"):
                yield Label("◈ ASSISTANT CHAT", classes="panel-title")
                yield Label("Interactive Agent Console", classes="panel-sub")

                # Controls: Model Selector + Agent Switch
                with Horizontal(id="controls-bar"):
                    yield Label("Model:", id="model-label")
                    yield Select([(m, m) for m in MODELS], value=MODELS[0], id="model-select")
                    yield Label("Agent:", id="agent-label")
                    yield Switch(value=False, id="agent-switch")

                # Chat message log
                yield RichLog(id="chat-window", highlight=True, markup=True)

                # Quick Automation Action Chips
                with Horizontal(id="chips-container"):
                    for idx, (lbl, _) in enumerate(QUICK_ACTIONS):
                        yield Button(lbl, classes="quick-chip", id=f"chip-{idx}")

                # Input Row
                with Horizontal(id="composer-row"):
                    yield Button("+", id="attach-btn", tooltip="Attach image or screenshot")
                    yield Input(placeholder="Type a task, automation command, or question...", id="chat-input")
                    yield Button("➤", id="send-btn")

        # Footer
        yield Label(
            "● System Ready  │  F1 Help  │  F2 Agent Mode  │  F3 Voice  │  F4 Screenshot  │  Ctrl+L Clear  │  Ctrl+C Quit",
            id="status-footer"
        )
        yield Footer()

    def on_mount(self):
        chat = self.query_one("#chat-window", RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        chat.write(
            f"[dim #8eb5ac][{ts}][/dim #8eb5ac] [bold #60ffb9]BenX AI Assistant v2.0[/bold #60ffb9]\n"
            f"[dim white]Connected to Arch Linux + Wayland (Hyprland). Native desktop automation, browser control, mobile ADB, and OpenRouter intelligence are fully operational.[/dim white]\n"
            f"[dim #61d8ff]⚡ Quick commands: screen OCR · workspace type · browser open · mobile ADB · system info[/dim #61d8ff]\n"
        )
        self._log_mission("BenX TUI mounted successfully.")
        self.query_one("#chat-input", Input).focus()
        threading.Thread(target=self._init_ai_engine, daemon=True).start()

    # ── Event Handlers ────────────────────────────────────────────────────────

    def on_input_submitted(self, event: Input.Submitted):
        if event.input.id == "chat-input":
            val = event.value.strip()
            event.input.value = ""
            if val:
                self.send_user_message(val)

    def on_button_pressed(self, event: Button.Pressed):
        bid = event.button.id
        if bid == "send-btn":
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

    def on_switch_changed(self, event: Switch.Changed):
        if event.switch.id == "agent-switch":
            self.agent_mode = event.value
            status = "AUTONOMOUS AGENT MODE" if event.value else "INSTANT COMMAND MODE"
            self._log_mission(f"Switched mode to: [bold #60ffb9]{status}[/bold #60ffb9]")
            self._set_status_bar(f"Mode: {status}")

    def on_select_changed(self, event: Select.Changed):
        if event.select.id == "model-select":
            val = str(event.value)
            tag = self.query_one("#top-model-tag", Label)
            if "deepseek" in val.lower():
                tag.update("[DeepSeek R1]")
            elif "gemini" in val.lower():
                tag.update("[Gemini 2.0]")
            elif "qwen" in val.lower():
                tag.update("[Qwen 2.5]")
            elif "claude" in val.lower():
                tag.update("[Claude 3.5]")
            elif "llama" in val.lower():
                tag.update("[Llama 3.3]")
            else:
                tag.update("[Auto Router]")
            self._log_mission(f"Selected AI model: {val}")

    # ── Command & Message Dispatch ────────────────────────────────────────────

    def send_user_message(self, text: str):
        if not text and not self.pending_image:
            return

        chat = self.query_one("#chat-window", RichLog)
        ts = datetime.now().strftime("%H:%M:%S")
        img_badge = f" [bold #61d8ff][📎 {os.path.basename(self.pending_image)}][/bold #61d8ff]" if self.pending_image else ""
        chat.write(f"\n[dim #8eb5ac][{ts}][/dim #8eb5ac] [bold cyan]👤 You:[/bold cyan] {text}{img_badge}")

        self._log_mission(f"User task: {text[:60]}")
        self._set_status_bar("⏳ BenX is processing...")

        # Process in background worker thread
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

            # Callback for ReAct agent step streaming
            def on_agent_step(step_text: str):
                self.app.call_from_thread(self._log_mission, f"[bold #b794ff]Step:[/bold #b794ff] {step_text[:75]}")

            if image_path:
                self.app.call_from_thread(self._log_mission, f"Analyzing image: {image_path}")
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
        except Exception as err:
            ts = datetime.now().strftime("%H:%M:%S")
            self.app.call_from_thread(chat.write, f"[dim #8eb5ac][{ts}][/dim #8eb5ac] [bold red]❌ Error:[/bold red] {err}")
            self.app.call_from_thread(self._log_mission, f"❌ Execution error: {err}")
            self.app.call_from_thread(self._set_status_bar, "✗ Error encountered")

    # ── Actions & Shortcuts ───────────────────────────────────────────────────

    def action_clear_chat(self):
        self.query_one("#chat-window", RichLog).clear()
        self._log_mission("Chat history cleared.")
        self._set_status_bar("Chat window cleared")

    def action_toggle_agent(self):
        sw = self.query_one("#agent-switch", Switch)
        sw.value = not sw.value

    def action_take_screen(self):
        """Take screenshot and attach for vision analysis"""
        try:
            from jarvis_ai.command_engine import CommandEngine
            res = CommandEngine.take_screenshot()
            # Find the saved screenshot path
            import glob
            files = sorted(glob.glob("/tmp/benx_screenshot_*.png"), key=os.path.getmtime, reverse=True)
            if files:
                self.pending_image = files[0]
                self._log_mission(f"📸 Screenshot attached: {self.pending_image}")
                inp = self.query_one("#chat-input", Input)
                inp.value = "analyze this screenshot"
                inp.focus()
                self._set_status_bar(f"Screenshot ready: {os.path.basename(self.pending_image)}")
            else:
                self._log_mission(f"Screenshot: {res}")
        except Exception as e:
            self._log_mission(f"Screenshot error: {e}")

    def action_voice_input(self):
        self._set_status_bar("🎤 Listening for voice input...")
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
        except Exception as exc:
            self.app.call_from_thread(self._set_status_bar, f"🎤 Voice error: {exc}")

    def action_show_help(self):
        chat = self.query_one("#chat-window", RichLog)
        chat.write(
            "\n[bold #60ffb9]══════════════════ BENX COMMANDS & SHORTCUTS ══════════════════[/bold #60ffb9]\n"
            "[bold #61d8ff]Shortcuts:[/bold #61d8ff]\n"
            "  [white]F1[/white]        Show this help guide\n"
            "  [white]F2[/white]        Toggle Autonomous ReAct Agent mode (ON/OFF)\n"
            "  [white]F3[/white]        Voice Recognition (Speech-to-Text)\n"
            "  [white]F4[/white]        Capture Desktop Screenshot & Prime for Vision Analysis\n"
            "  [white]Ctrl+L[/white]    Clear current chat log\n"
            "  [white]Ctrl+C[/white]    Quit BenX TUI\n\n"
            "[bold #61d8ff]Automation Commands:[/bold #61d8ff]\n"
            "  [cyan]open <app>[/cyan]                     Open local desktop applications\n"
            "  [cyan]in workspace <N> type <cmd>[/cyan]   Direct keystroke injection into workspace\n"
            "  [cyan]analyze my screen[/cyan]              Vision OCR and desktop inspection\n"
            "  [cyan]automate <instructions>[/cyan]        Multi-step desktop/browser workflow\n"
            "  [cyan]mobile tap <text|x,y>[/cyan]          Send touch event to connected Android phone\n"
            "  [cyan]system info[/cyan]                    Display battery, CPU, RAM, and network\n"
            "[bold #60ffb9]═══════════════════════════════════════════════════════════════[/bold #60ffb9]\n"
        )

    # ── Internal Helpers ──────────────────────────────────────────────────────

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
                f"● {status}  │  F1 Help  │  F2 Agent Mode  │  F3 Voice  │  F4 Screenshot  │  Ctrl+L Clear  │  Ctrl+C Quit"
            )
        except Exception:
            pass


if __name__ == "__main__":
    BenXTUI().run()

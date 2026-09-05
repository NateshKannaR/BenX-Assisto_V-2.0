"""
BenX Settings Window - Modern Libadwaita Preferences Window for BenX configuration.
"""
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib
import logging
import os
from pathlib import Path
from jarvis_ai.config import Config

logger = logging.getLogger(__name__)

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "benx.desktop"


class BenXSettingsWindow(Adw.PreferencesWindow):
    """Native Libadwaita preferences window for AI models, API keys, and system automation."""

    def __init__(self, parent_window=None, on_settings_saved=None):
        super().__init__()
        self.set_title("BenX Settings")
        self.set_default_size(680, 560)
        self.set_modal(True)
        if parent_window:
            self.set_transient_for(parent_window)
        self.on_settings_saved = on_settings_saved

        self._build_pages()

    def _build_pages(self):
        # ── Page 1: AI & Intelligence ─────────────────────────────────────────
        ai_page = Adw.PreferencesPage()
        ai_page.set_title("AI & Models")
        ai_page.set_icon_name("preferences-system-symbolic")
        self.add(ai_page)

        # Provider & Model Group
        model_group = Adw.PreferencesGroup()
        model_group.set_title("AI Intelligence & Model Routing")
        model_group.set_description("Select your preferred AI model and configure API keys.")
        ai_page.add(model_group)

        # Model Selector ComboRow
        self.model_row = Adw.ComboRow()
        self.model_row.set_title("Active AI Model")
        self.model_row.set_subtitle("Powers conversation, reasoning, and autonomous automation")

        self.model_list = [
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-r1",
            "google/gemini-2.0-flash-001",
            "qwen/qwen-2.5-72b-instruct",
            "anthropic/claude-3.5-sonnet",
            "llama-3.3-70b-versatile (Groq)",
            "llama-3.1-8b-instant (Groq Fast)",
        ]
        string_list = Gtk.StringList.new(self.model_list)
        self.model_row.set_model(string_list)

        # Set current selection
        curr_model = getattr(Config, "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
        idx = 0
        for i, m in enumerate(self.model_list):
            if m.split()[0] in curr_model:
                idx = i
                break
        self.model_row.set_selected(idx)
        self.model_row.connect("notify::selected", self._on_model_changed)
        model_group.add(self.model_row)

        # OpenRouter API Key
        self.openrouter_key_row = Adw.PasswordEntryRow()
        self.openrouter_key_row.set_title("OpenRouter API Key")
        self.openrouter_key_row.set_text(getattr(Config, "OPENROUTER_KEY", "") or "")
        model_group.add(self.openrouter_key_row)

        # Groq API Key
        self.groq_key_row = Adw.PasswordEntryRow()
        self.groq_key_row.set_title("Groq API Key")
        self.groq_key_row.set_text(getattr(Config, "GROQ_KEY", "") or "")
        model_group.add(self.groq_key_row)

        # ── Page 2: System & Wayland Automation ──────────────────────────────
        sys_page = Adw.PreferencesPage()
        sys_page.set_title("System & Wayland")
        sys_page.set_icon_name("preferences-desktop-display-symbolic")
        self.add(sys_page)

        # Hyprland Rules Group
        hypr_group = Adw.PreferencesGroup()
        hypr_group.set_title("Hyprland Event Automation")
        hypr_group.set_description("Live event triggers responding to window and monitor socket events.")
        sys_page.add(hypr_group)

        self.pip_row = Adw.SwitchRow()
        self.pip_row.set_title("Auto-Float Picture-in-Picture")
        self.pip_row.set_subtitle("Automatically float and pin videos when opened")
        self.pip_row.set_active(True)
        hypr_group.add(self.pip_row)

        self.music_ws_row = Adw.SwitchRow()
        self.music_ws_row.set_title("Auto-Route Music to Workspace 9")
        self.music_ws_row.set_subtitle("Sends Spotify / audio players silently to workspace 9")
        self.music_ws_row.set_active(True)
        hypr_group.add(self.music_ws_row)

        self.dock_row = Adw.SwitchRow()
        self.dock_row.set_title("Multi-Monitor Docking Profiles")
        self.dock_row.set_subtitle("Auto-assign workspaces when external monitors are plugged in")
        self.dock_row.set_active(True)
        hypr_group.add(self.dock_row)

        # Autostart Group
        boot_group = Adw.PreferencesGroup()
        boot_group.set_title("Startup & Peripherals")
        sys_page.add(boot_group)

        self.autostart_row = Adw.SwitchRow()
        self.autostart_row.set_title("Launch BenX on Startup")
        self.autostart_row.set_subtitle("Automatically start BenX in floating compact mode upon login")
        self.autostart_row.set_active(AUTOSTART_FILE.exists())
        self.autostart_row.connect("notify::active", self._on_autostart_toggled)
        boot_group.add(self.autostart_row)

        self.wake_word_row = Adw.SwitchRow()
        self.wake_word_row.set_title("Always-On Wake Word ('Hey BenX')")
        self.wake_word_row.set_subtitle("Listen for voice commands in the background")
        self.wake_word_row.set_active(False)
        boot_group.add(self.wake_word_row)

        # Save Button Row
        save_group = Adw.PreferencesGroup()
        save_btn = Gtk.Button(label="Save & Apply Configuration")
        save_btn.add_css_class("suggested-action")
        save_btn.set_margin_top(14)
        save_btn.connect("clicked", self._on_save_clicked)
        save_group.add(save_btn)
        sys_page.add(save_group)

    def _on_model_changed(self, row, param):
        selected_idx = row.get_selected()
        selected_name = self.model_list[selected_idx].split()[0]
        logger.info(f"Model selected: {selected_name}")

    def _on_autostart_toggled(self, row, param):
        enable = row.get_active()
        try:
            if enable:
                AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
                benx_py = Path(__file__).resolve().parent.parent.parent / "benx.py"
                desktop_entry = f"""[Desktop Entry]
Type=Application
Name=BenX AI Assistant
Comment=Adaptive Linux Control & Automation Platform
Exec=/usr/bin/python3 {benx_py}
Icon=benx
Terminal=false
Categories=Utility;ArtificialIntelligence;
X-GNOME-Autostart-enabled=true
"""
                AUTOSTART_FILE.write_text(desktop_entry, encoding="utf-8")
                logger.info(f"Created autostart entry: {AUTOSTART_FILE}")
            else:
                if AUTOSTART_FILE.exists():
                    AUTOSTART_FILE.unlink()
                    logger.info("Removed autostart entry")
        except Exception as e:
            logger.error(f"Failed to toggle autostart: {e}")

    def _on_save_clicked(self, btn):
        selected_idx = self.model_row.get_selected()
        selected_name = self.model_list[selected_idx].split()[0]
        or_key = self.openrouter_key_row.get_text().strip()
        groq_key = self.groq_key_row.get_text().strip()

        # Update in-memory Config
        Config.OPENROUTER_MODEL = selected_name
        if or_key:
            Config.OPENROUTER_KEY = or_key
            os.environ["OPENROUTER_API_KEY"] = or_key
        if groq_key:
            Config.GROQ_KEY = groq_key
            os.environ["GROQ_API_KEY"] = groq_key

        # Persist to workspace .env file
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        try:
            lines = []
            if env_path.exists():
                lines = env_path.read_text(encoding="utf-8").splitlines()

            new_lines = []
            keys_set = set()
            for line in lines:
                if line.startswith("OPENROUTER_API_KEY="):
                    if or_key:
                        new_lines.append(f"OPENROUTER_API_KEY={or_key}")
                        keys_set.add("OPENROUTER_API_KEY")
                elif line.startswith("GROQ_API_KEY="):
                    if groq_key:
                        new_lines.append(f"GROQ_API_KEY={groq_key}")
                        keys_set.add("GROQ_API_KEY")
                elif line.startswith("OPENROUTER_MODEL="):
                    new_lines.append(f"OPENROUTER_MODEL={selected_name}")
                    keys_set.add("OPENROUTER_MODEL")
                else:
                    new_lines.append(line)

            if "OPENROUTER_API_KEY" not in keys_set and or_key:
                new_lines.append(f"OPENROUTER_API_KEY={or_key}")
            if "GROQ_API_KEY" not in keys_set and groq_key:
                new_lines.append(f"GROQ_API_KEY={groq_key}")
            if "OPENROUTER_MODEL" not in keys_set:
                new_lines.append(f"OPENROUTER_MODEL={selected_name}")

            env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            logger.info("Saved configuration to .env")
        except Exception as e:
            logger.error(f"Failed to persist .env: {e}")

        if self.on_settings_saved:
            try:
                self.on_settings_saved({
                    "model": selected_name,
                    "wake_word": self.wake_word_row.get_active(),
                    "auto_pip": self.pip_row.get_active(),
                    "auto_music": self.music_ws_row.get_active(),
                })
            except Exception as e:
                logger.error(f"Callback error: {e}")

        self.close()

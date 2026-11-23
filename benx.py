#!/usr/bin/env python3
"""
BenX - Advanced AI Assistant with Beautiful GTK4 UI
Main entry point
"""
import argparse
import importlib.util
import os
import shutil
import sys
import signal
import logging
from datetime import datetime

# Setup logging
from jarvis_ai.config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Check system monitor
try:
    from jarvis_ai.system_monitor import start_monitor as _start_monitor
    MONITOR_AVAILABLE = True
except ImportError:
    MONITOR_AVAILABLE = False

# Check wake-word engine
try:
    from jarvis_ai.wake_word_engine import WakeWordEngine
    WAKE_WORD_AVAILABLE = True
except ImportError:
    WAKE_WORD_AVAILABLE = False


class BenX:
    """Main BenX application"""
    
    def __init__(self, use_gui: bool = True):
        self.running = True
        self.use_gui = use_gui
        if not use_gui:
            self.setup_signal_handlers()
        self._monitor = None
        self._wake_word = None
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\nBenX: Shutting down gracefully... 👋")
        self.running = False
        if self._monitor:
            self._monitor.stop()

    def _start_background_services(self, ai_engine=None):
        """Start background services: system monitor + wake-word."""
        # System monitor
        if MONITOR_AVAILABLE:
            try:
                self._monitor = _start_monitor(ai_engine=ai_engine)
                logger.info("✅ System monitor started")
            except Exception as e:
                logger.warning(f"System monitor failed to start: {e}")

        # Wake-word engine (runs in its own daemon thread)
        if WAKE_WORD_AVAILABLE:
            try:
                self._wake_word = WakeWordEngine()
                self._wake_word.start()
                logger.info("✅ Wake-word engine started")
            except Exception as e:
                logger.warning(f"Wake-word engine failed to start: {e}")
    
    def save_command(self, command: str):
        """Save command to history"""
        try:
            with open(Config.HISTORY_FILE, 'a', encoding='utf-8') as f:
                f.write(f"{datetime.now().isoformat()}: {command}\n")
        except Exception as e:
            logger.warning(f"Failed to save command: {e}")
    
    def run(self):
        if self.use_gui:
            from jarvis_ai.gui.beautiful_gtk4 import BeautifulBenXGTK4App
            BeautifulBenXGTK4App(self).run_app()
        else:
            self.run_cli()

    def run_cli(self):
        """Run in CLI mode"""
        print("=" * 60)
        print("🎯 BenX - Advanced Assistant with RAG & Image Sensing")
        print("=" * 60)
        print("\nType 'help' for commands or just speak naturally!")
        print("Examples: 'open chrome', 'volume 80', 'what\'s the weather'")
        print("=" * 60 + "\n")
        
        logger.info("BenX started (CLI mode)")
        from jarvis_ai.ai_engine import AIEngine
        from jarvis_ai.executor import CommandExecutor
        
        ai_engine = AIEngine()

        # Start background services
        self._start_background_services(ai_engine)

        while self.running:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                self.save_command(user_input)
                user_lower = user_input.lower()
                
                if user_lower in ["exit", "quit", "bye"]:
                    print("BenX: Goodbye! Have a great day! 👋")
                    break
                
                print("🧠 Understanding...")
                json_cmd = ai_engine.interpret_command(
                    user_input,
                    conversation_context=ai_engine.conversation_history,
                    learning_engine=ai_engine.learning_engine
                )
                result = CommandExecutor.execute(json_cmd, ai_engine, user_input)
                
                if result is None:
                    print("🧠 Thinking deeply...")
                    response = ai_engine.chat(user_input)
                    print(f"BenX: {response}\n")
                else:
                    print(f"BenX: {result}\n")
                    
            except EOFError:
                print("\nBenX: Input closed. Goodbye! 👋")
                break
            except KeyboardInterrupt:
                print("\nBenX: Interrupted. Goodbye! 👋")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                print(f"BenX: ❌ Unexpected error: {str(e)}\n")


def main():
    parser = argparse.ArgumentParser(description="BenX desktop assistant")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--tui", "-t", action="store_true", help="launch the terminal UI (default)")
    mode.add_argument("--gtk", "--gtk4", "--gui", action="store_true", help="launch GTK4")
    mode.add_argument("--cli", "--no-gui", action="store_true", help="launch the text prompt")
    mode.add_argument("--web", action="store_true", help="serve the local web UI")
    mode.add_argument("--doctor", action="store_true", help="check optional dependencies")
    args = parser.parse_args()
    try:
        if args.doctor:
            from jarvis_ai.hyprland.ipc import HyprlandIPC
            for command in ("hyprctl", "grim", "slurp", "cliphist", "wl-copy", "ydotool", "nmcli", "tesseract"):
                print(f"{command}: {'available' if shutil.which(command) else 'missing'}")
            print(f"Hyprland session: {'reachable' if HyprlandIPC.is_available() else 'unavailable'}")
            print(f"Textual: {'available' if importlib.util.find_spec('textual') else 'missing'}")
            try:
                import gi
                gi.require_version("Gtk", "4.0")
                gi.require_version("Adw", "1")
                from gi.repository import Adw, Gtk
                print("GTK4 / Libadwaita: available")
            except (ImportError, ValueError):
                print("GTK4 / Libadwaita: missing")
            print(f"AI provider: {'configured' if Config.GROQ_KEY or Config.OPENROUTER_KEY else 'unconfigured'}")
            print(f"MongoDB: {'configured' if Config.MONGODB_URI else 'local storage'}")
        elif args.web:
            import uvicorn
            uvicorn.run("src.main:app", host="127.0.0.1", port=int(os.getenv("BENX_PORT", "8000")))
        elif args.gtk or args.cli:
            BenX(use_gui=args.gtk).run()
        else:
            from benx_tui import BenXTUI
            BenXTUI().run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

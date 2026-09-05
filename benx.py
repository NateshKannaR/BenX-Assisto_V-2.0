#!/usr/bin/env python3
"""
BenX - Advanced AI Assistant with Beautiful GTK4 UI
Main entry point
"""
import sys
import signal
import logging
from datetime import datetime
from pathlib import Path

# CRITICAL: Load GTK4 BEFORE anything else
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

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

# Check GTK4 availability
try:
    from jarvis_ai.gui import beautiful_gtk4
    GUI_AVAILABLE = True
except ImportError as e:
    GUI_AVAILABLE = False
    logger.warning(f"Beautiful GTK4 GUI not available: {e}")

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
        self.use_gui = use_gui and GUI_AVAILABLE
        self.setup_signal_handlers()
        self.gui = None
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
        if self.gui and self.gui.root:
            try:
                self.gui.root.quit()
            except:
                pass

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
        """Main application loop"""
        if "--tui" in sys.argv or "-t" in sys.argv:
            from benx_tui import BenXTUI
            BenXTUI().run()
            return

        if "--gtk" in sys.argv or "--gtk4" in sys.argv:
            try:
                from jarvis_ai.gui.beautiful_gtk4 import BeautifulBenXGTK4App
                app = BeautifulBenXGTK4App(self)
                app.run_app()
                return
            except Exception as e:
                logger.error(f"GTK4 failed: {e}")
                print(f"⚠️ GTK4 failed to launch ({e}), launching upgraded TUI...")
                from benx_tui import BenXTUI
                BenXTUI().run()
                return

        if self.use_gui:
            print("🚀 Starting BenX Web UI at http://localhost:8000")
            print("   Open your browser to http://localhost:8000")
            try:
                import subprocess
                src_main = Path(__file__).parent / 'src' / 'main.py'
                subprocess.Popen(
                    [sys.executable, str(src_main)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                import time
                time.sleep(1.5)
                subprocess.Popen(
                    ['xdg-open', 'http://localhost:8000'],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                # Keep alive
                while self.running:
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Web UI failed: {e}")
                print(f"⚠️ Web UI failed ({e}), launching upgraded TUI...")
                from benx_tui import BenXTUI
                BenXTUI().run()
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
    """Main entry point"""
    try:
        use_gui = "--no-gui" not in sys.argv
        
        jarvis = BenX(use_gui=use_gui)
        jarvis.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

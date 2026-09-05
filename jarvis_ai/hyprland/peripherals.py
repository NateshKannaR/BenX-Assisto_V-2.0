"""
Hyprland Wayland Peripherals - Screenshots (grim/slurp), screen recording (wf-recorder),
clipboard history (cliphist/wl-clipboard), notifications (dunst/mako), and lock (hyprlock).
"""
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from jarvis_ai.hyprland.ipc import HyprlandIPC

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = Path.home() / "Pictures" / "Screenshots"
RECORDINGS_DIR = Path.home() / "Videos" / "Recordings"


class PeripheralsManager:
    """Manages Wayland peripherals without any X11 dependencies."""

    _recording_proc: Optional[subprocess.Popen] = None
    _recording_file: Optional[Path] = None

    @staticmethod
    def _ensure_dirs():
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    # ── Screenshots (grim / slurp) ──────────────────────────────────────────

    @staticmethod
    def screenshot_fullscreen(output_path: Optional[str] = None) -> str:
        """Captures full screen via grim."""
        if not shutil.which("grim"):
            return "❌ 'grim' is not installed. Install via: sudo pacman -S grim"

        PeripheralsManager._ensure_dirs()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = Path(output_path) if output_path else SCREENSHOTS_DIR / f"benx_shot_{ts}.png"

        try:
            r = subprocess.run(["grim", str(target)], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and target.exists():
                # Also copy to clipboard via wl-copy
                if shutil.which("wl-copy"):
                    subprocess.run(["wl-copy", "--type", "image/png"], input=target.read_bytes())
                return f"📸 Screenshot saved to {target} and copied to clipboard."
            return f"❌ grim failed: {r.stderr.strip()}"
        except Exception as e:
            return f"❌ Screenshot error: {e}"

    @staticmethod
    def screenshot_region(output_path: Optional[str] = None) -> str:
        """Interactive region screenshot using slurp + grim."""
        if not shutil.which("grim") or not shutil.which("slurp"):
            return "❌ 'grim' and 'slurp' are required. Install via: sudo pacman -S grim slurp"

        PeripheralsManager._ensure_dirs()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = Path(output_path) if output_path else SCREENSHOTS_DIR / f"benx_crop_{ts}.png"

        try:
            # Run slurp to get region
            s = subprocess.run(["slurp"], capture_output=True, text=True, timeout=15)
            region = s.stdout.strip()
            if not region:
                return "⚠️ Selection cancelled."

            r = subprocess.run(["grim", "-g", region, str(target)], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and target.exists():
                if shutil.which("wl-copy"):
                    subprocess.run(["wl-copy", "--type", "image/png"], input=target.read_bytes())
                return f"📸 Region screenshot saved to {target}."
            return f"❌ grim region error: {r.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "⚠️ Screenshot selection timed out."
        except Exception as e:
            return f"❌ Region screenshot error: {e}"

    @staticmethod
    def screenshot_active_window(output_path: Optional[str] = None) -> str:
        """Captures the geometry of the active window using hyprctl activewindow + grim."""
        if not shutil.which("grim"):
            return "❌ 'grim' is not installed."

        active = HyprlandIPC.get_active_window()
        if not active or "at" not in active or "size" not in active:
            return PeripheralsManager.screenshot_fullscreen(output_path)

        x, y = active["at"]
        w, h = active["size"]
        geom = f"{x},{y} {w}x{h}"

        PeripheralsManager._ensure_dirs()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = Path(output_path) if output_path else SCREENSHOTS_DIR / f"benx_win_{ts}.png"

        try:
            r = subprocess.run(["grim", "-g", geom, str(target)], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and target.exists():
                if shutil.which("wl-copy"):
                    subprocess.run(["wl-copy", "--type", "image/png"], input=target.read_bytes())
                return f"📸 Active window screenshot saved to {target}."
            return f"❌ grim window error: {r.stderr.strip()}"
        except Exception as e:
            return f"❌ Active window screenshot error: {e}"

    # ── Screen Recording (wf-recorder) ──────────────────────────────────────

    @staticmethod
    def is_recording() -> bool:
        return (
            PeripheralsManager._recording_proc is not None
            and PeripheralsManager._recording_proc.poll() is None
        )

    @staticmethod
    def start_recording(with_audio: bool = False, output_path: Optional[str] = None) -> str:
        """Starts background screen recording with wf-recorder."""
        if not shutil.which("wf-recorder"):
            return "⚠️ 'wf-recorder' is not installed. Install via: sudo pacman -S wf-recorder"

        if PeripheralsManager.is_recording():
            return f"⚠️ Already recording to {PeripheralsManager._recording_file}."

        PeripheralsManager._ensure_dirs()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = Path(output_path) if output_path else RECORDINGS_DIR / f"benx_rec_{ts}.mp4"

        cmd = ["wf-recorder", "-f", str(target)]
        if with_audio:
            cmd.append("-a")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            PeripheralsManager._recording_proc = proc
            PeripheralsManager._recording_file = target
            PeripheralsManager.send_notification("BenX Screen Recorder", f"Recording started: {target.name}")
            return f"🎥 Screen recording started -> {target}"
        except Exception as e:
            return f"❌ Failed to start screen recording: {e}"

    @staticmethod
    def stop_recording() -> str:
        """Stops active screen recording."""
        if not PeripheralsManager.is_recording():
            return "⚠️ No active screen recording found."

        try:
            proc = PeripheralsManager._recording_proc
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

        saved_file = PeripheralsManager._recording_file
        PeripheralsManager._recording_proc = None
        PeripheralsManager._recording_file = None
        PeripheralsManager.send_notification("BenX Screen Recorder", f"Recording saved to {saved_file}")
        return f"✅ Screen recording saved: {saved_file}"

    # ── Clipboard History (cliphist / wl-clipboard) ─────────────────────────

    @staticmethod
    def clipboard_history(limit: int = 15) -> str:
        """Returns the recent clipboard entries from cliphist."""
        if not shutil.which("cliphist"):
            return "⚠️ 'cliphist' is not installed. Install via: sudo pacman -S cliphist"

        try:
            r = subprocess.run(["cliphist", "list"], capture_output=True, text=True, timeout=4)
            if r.returncode != 0 or not r.stdout.strip():
                return "📋 Clipboard history is currently empty."

            lines = r.stdout.strip().splitlines()[:limit]
            formatted = ["📋 RECENT CLIPBOARD HISTORY:"]
            for line in lines:
                parts = line.split("\t", 1)
                idx = parts[0]
                text = parts[1][:70] if len(parts) > 1 else ""
                formatted.append(f"  [{idx}] {text}")
            return "\n".join(formatted)
        except Exception as e:
            return f"❌ Failed to read clipboard history: {e}"

    @staticmethod
    def clipboard_search(query: str) -> str:
        """Searches clipboard history for query string."""
        if not shutil.which("cliphist"):
            return "⚠️ 'cliphist' is not installed."

        try:
            r = subprocess.run(["cliphist", "list"], capture_output=True, text=True, timeout=4)
            matches = [line for line in r.stdout.splitlines() if query.lower() in line.lower()]
            if not matches:
                return f"📋 No clipboard entries matching '{query}' found."

            formatted = [f"📋 Clipboard matches for '{query}':"]
            for m in matches[:10]:
                parts = m.split("\t", 1)
                idx = parts[0]
                content = parts[1][:80] if len(parts) > 1 else ""
                formatted.append(f"  [{idx}] {content}")
            return "\n".join(formatted)
        except Exception as e:
            return f"❌ Clipboard search error: {e}"

    @staticmethod
    def clipboard_paste_item(item_id: str) -> str:
        """Decodes a cliphist item and sets it into the active Wayland clipboard."""
        if not shutil.which("cliphist") or not shutil.which("wl-copy"):
            return "⚠️ Required clipboard tools missing."

        try:
            # cliphist decode <id> | wl-copy
            r_dec = subprocess.run(["cliphist", "decode", str(item_id)], capture_output=True, timeout=4)
            if r_dec.returncode == 0:
                subprocess.run(["wl-copy"], input=r_dec.stdout, timeout=4)
                return f"✅ Copied clipboard item [{item_id}] to active clipboard."
            return f"❌ Item [{item_id}] not found in clipboard history."
        except Exception as e:
            return f"❌ Paste decode error: {e}"

    @staticmethod
    def clipboard_wipe() -> str:
        """Wipes cliphist clipboard history."""
        if not shutil.which("cliphist"):
            return "⚠️ 'cliphist' not installed."
        try:
            subprocess.run(["cliphist", "wipe"], timeout=4)
            return "✅ Clipboard history wiped."
        except Exception as e:
            return f"❌ Failed to wipe clipboard: {e}"

    # ── Notifications & Session Lock ────────────────────────────────────────

    @staticmethod
    def detect_notification_daemon() -> str:
        """Detects whether dunst, mako, or generic notification daemon is active."""
        try:
            p = subprocess.run(["pgrep", "-l", "dunst"], capture_output=True, text=True)
            if p.returncode == 0:
                return "dunst"
            p = subprocess.run(["pgrep", "-l", "mako"], capture_output=True, text=True)
            if p.returncode == 0:
                return "mako"
        except Exception:
            pass
        return "notify-send"

    @staticmethod
    def send_notification(title: str, message: str, urgency: str = "normal") -> bool:
        """Sends a desktop notification via notify-send."""
        if not shutil.which("notify-send"):
            return False
        try:
            subprocess.run(
                ["notify-send", "-a", "BenX AI", "-u", urgency, title, message],
                timeout=3
            )
            return True
        except Exception:
            return False

    @staticmethod
    def lock_screen() -> str:
        """Locks the screen via hyprlock if present, otherwise loginctl lock-session."""
        if shutil.which("hyprlock"):
            subprocess.Popen(["hyprlock"])
            return "🔒 Screen locked via hyprlock."
        if shutil.which("loginctl"):
            subprocess.run(["loginctl", "lock-session"])
            return "🔒 Screen locked via loginctl."
        return "❌ Neither hyprlock nor loginctl is available."

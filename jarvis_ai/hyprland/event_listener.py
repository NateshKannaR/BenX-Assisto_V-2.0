"""
Hyprland Socket2 Event Listener - Real-time IPC event stream automation for BenX.
Listens to openwindow, closewindow, workspace, monitor changes, and executes dynamic triggers.
"""
import logging
import socket
import threading
import time
from typing import Callable, Dict, List, Optional
from jarvis_ai.hyprland.ipc import HyprlandIPC

logger = logging.getLogger(__name__)


class HyprlandEventListener:
    """
    Subscribes directly to Hyprland's Unix socket (.socket2.sock) and streams events.
    Enables instant reactions to windows opening, closing, moving, or monitors plugging in.
    """

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._callbacks: Dict[str, List[Callable[[str], None]]] = {}
        self._auto_pip_float = True
        self._auto_music_workspace = True
        self._music_workspace = "9"
        self._auto_dock_layout = True

        # Register built-in automation rules
        self.register_callback("openwindow", self._on_open_window)
        self.register_callback("monitoradded", self._on_monitor_changed)
        self.register_callback("monitorremoved", self._on_monitor_changed)

    def register_callback(self, event_type: str, callback: Callable[[str], None]):
        """Registers a callback for an event (e.g. 'openwindow', 'workspace', 'activewindow')."""
        self._callbacks.setdefault(event_type, []).append(callback)

    def unregister_callback(self, event_type: str, callback: Callable[[str], None]):
        """Unregisters an event callback."""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)

    def start(self):
        """Starts the event listener daemon thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="benx-hyprland-socket2")
        self._thread.start()
        logger.info("✅ Hyprland socket2 event listener started")

    def stop(self):
        """Stops the event listener."""
        self._running = False

    def _listen_loop(self):
        while self._running:
            sock_path = HyprlandIPC.get_socket2_path()
            if not sock_path or not socket:
                time.sleep(2)
                continue

            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(sock_path)
                logger.info(f"Connected to Hyprland socket2 at {sock_path}")

                buffer = ""
                while self._running:
                    data = s.recv(4096)
                    if not data:
                        break
                    buffer += data.decode("utf-8", errors="ignore")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._dispatch_event(line)
                s.close()
            except Exception as e:
                logger.debug(f"Hyprland socket2 loop reconnecting: {e}")
                time.sleep(1.5)

    def _dispatch_event(self, raw_line: str):
        """Dispatches event line: 'event>>data' to registered callbacks."""
        if ">>" not in raw_line:
            return
        event, data = raw_line.split(">>", 1)
        event = event.strip()

        callbacks = self._callbacks.get(event, [])
        for cb in callbacks:
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Error in Hyprland event callback for {event}: {e}")

        # Also trigger wildcard callbacks
        for cb in self._callbacks.get("*", []):
            try:
                cb(f"{event}>>{data}")
            except Exception:
                pass

    # ── Built-in Event Automations ──────────────────────────────────────────

    def _on_open_window(self, data: str):
        """
        Triggered when a window opens.
        Data format: '<window_address>,<workspace_name>,<window_class>,<window_title>'
        """
        parts = data.split(",")
        if len(parts) < 4:
            return

        addr, ws_name, win_class, win_title = parts[0], parts[1], parts[2], parts[3]
        title_lower = win_title.lower()
        class_lower = win_class.lower()

        # 1. Auto-float Picture-in-Picture windows
        if self._auto_pip_float:
            if "picture-in-picture" in title_lower or "picture in picture" in title_lower:
                logger.info(f"🎯 Auto-floating Picture-in-Picture window [{win_class}] {win_title}")
                HyprlandIPC.dispatch("focuswindow", f"address:0x{addr.lstrip('0x')}")
                HyprlandIPC.dispatch("setfloating", "address:0x{addr.lstrip('0x')}")
                HyprlandIPC.dispatch("pin", f"address:0x{addr.lstrip('0x')}")
                return

        # 2. Auto-move music/audio apps to dedicated workspace (e.g. Spotify)
        if self._auto_music_workspace:
            if "spotify" in class_lower or "apple music" in title_lower or "rhythmbox" in class_lower:
                if ws_name != self._music_workspace:
                    logger.info(f"🎵 Auto-moving Spotify to music workspace {self._music_workspace}")
                    HyprlandIPC.dispatch(
                        "movetoworkspacesilent",
                        f"{self._music_workspace},address:0x{addr.lstrip('0x')}"
                    )
                    return

    def _on_monitor_changed(self, data: str):
        """Triggered when monitors are connected or disconnected."""
        if not self._auto_dock_layout:
            return
        logger.info(f"🖥️ Monitor topology changed ({data}). Checking docked profile...")
        try:
            from jarvis_ai.hyprland.monitor import MonitorManager
            state = MonitorManager.detect_docked_state()
            MonitorManager.apply_profile(state)
        except Exception as e:
            logger.warning(f"Failed to auto-apply monitor profile: {e}")

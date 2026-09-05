"""
Hyprland Window Manager - Full control over Wayland windows in Hyprland.
"""
import logging
from typing import Any, Dict, List, Optional
from jarvis_ai.hyprland.ipc import HyprlandIPC

logger = logging.getLogger(__name__)


class WindowManager:
    """Provides high-level window control: move, resize, float/tile, pin, focus, group."""

    @staticmethod
    def get_active_window() -> Optional[Dict[str, Any]]:
        """Returns details of the currently focused window."""
        return HyprlandIPC.get_active_window()

    @staticmethod
    def get_all_windows() -> List[Dict[str, Any]]:
        """Returns all open client windows across all workspaces."""
        return HyprlandIPC.get_clients()

    @staticmethod
    def find_windows(query: str) -> List[Dict[str, Any]]:
        """Finds windows matching class, title, or address."""
        if not query:
            return []
        q = query.lower().strip()
        matches = []
        for c in WindowManager.get_all_windows():
            cls = c.get("class", "").lower()
            title = c.get("title", "").lower()
            addr = c.get("address", "").lower()
            if q in cls or q in title or q == addr:
                matches.append(c)
        return matches

    @staticmethod
    def focus_window(query: str) -> str:
        """Focuses a window by app class, title keyword, or window address."""
        matches = WindowManager.find_windows(query)
        if not matches:
            return f"❌ No window matching '{query}' found."

        target = matches[0]
        addr = target.get("address", "")
        ws_id = target.get("workspace", {}).get("id")
        title = target.get("title", "Window")
        cls = target.get("class", "")

        # Dispatch focus by address
        if HyprlandIPC.dispatch("focuswindow", f"address:{addr}"):
            if ws_id is not None:
                HyprlandIPC.dispatch("workspace", str(ws_id))
            return f"✅ Focused [{cls}] '{title}' on workspace {ws_id}."
        return f"❌ Failed to focus window '{query}'."

    @staticmethod
    def close_window(query: Optional[str] = None) -> str:
        """Closes the specified window or the active window if query is None."""
        if query:
            matches = WindowManager.find_windows(query)
            if not matches:
                return f"❌ No window matching '{query}' found to close."
            addr = matches[0].get("address", "")
            if HyprlandIPC.dispatch("closewindow", f"address:{addr}"):
                return f"✅ Closed window '{matches[0].get('title')}'."
            return f"❌ Failed to close window '{query}'."

        if HyprlandIPC.dispatch("killactive"):
            return "✅ Closed active window."
        return "❌ Failed to close active window."

    @staticmethod
    def toggle_float(query: Optional[str] = None) -> str:
        """Toggles floating state for active window or matching target."""
        if query:
            matches = WindowManager.find_windows(query)
            if matches:
                addr = matches[0].get("address", "")
                HyprlandIPC.dispatch("focuswindow", f"address:{addr}")
        if HyprlandIPC.dispatch("togglefloating"):
            return "✅ Toggled floating state."
        return "❌ Failed to toggle floating state."

    @staticmethod
    def set_floating(enable: bool, query: Optional[str] = None) -> str:
        """Explicitly sets floating or tiled mode."""
        win = None
        if query:
            matches = WindowManager.find_windows(query)
            if matches:
                win = matches[0]
                HyprlandIPC.dispatch("focuswindow", f"address:{win.get('address')}")
        else:
            win = WindowManager.get_active_window()

        if win:
            current_float = bool(win.get("floating", False))
            if current_float != enable:
                HyprlandIPC.dispatch("togglefloating")
            state = "floating" if enable else "tiled"
            return f"✅ Window set to {state}."
        return WindowManager.toggle_float(query)

    @staticmethod
    def toggle_pin(query: Optional[str] = None) -> str:
        """Pins a floating window across all workspaces."""
        if query:
            matches = WindowManager.find_windows(query)
            if matches:
                HyprlandIPC.dispatch("focuswindow", f"address:{matches[0].get('address')}")
        if HyprlandIPC.dispatch("pin"):
            return "✅ Toggled window pin status."
        return "❌ Failed to pin window (window must be floating)."

    @staticmethod
    def toggle_fullscreen(mode: int = 0) -> str:
        """Toggles fullscreen mode (0: fullscreen, 1: maximize/monocle)."""
        if HyprlandIPC.dispatch("fullscreen", str(mode)):
            mode_desc = "monocle maximize" if mode == 1 else "fullscreen"
            return f"✅ Toggled {mode_desc}."
        return "❌ Failed to toggle fullscreen."

    @staticmethod
    def move_active(direction_or_pos: str) -> str:
        """
        Moves the active window.
        Directions: 'left', 'right', 'up', 'down' (e.g. 'movewindow l')
        Coordinates / pixels: e.g. '+50 0', '100 200'
        """
        d = direction_or_pos.lower().strip()
        dir_map = {
            "left": "l", "l": "l",
            "right": "r", "r": "r",
            "up": "u", "u": "u",
            "down": "d", "d": "d"
        }
        if d in dir_map:
            if HyprlandIPC.dispatch("movewindow", dir_map[d]):
                return f"✅ Moved window {d}."
        elif " " in d:
            # Absolute or relative coordinate move
            if HyprlandIPC.dispatch("moveactive", d):
                return f"✅ Moved active window by {d}."
        return f"❌ Failed to move window ({direction_or_pos})."

    @staticmethod
    def resize_active(direction_or_delta: str) -> str:
        """
        Resizes active window.
        Directions: 'grow', 'shrink', 'larger', 'smaller'
        Pixel deltas: e.g. '50 50', '-50 0'
        """
        d = direction_or_delta.lower().strip()
        deltas = {
            "grow": "60 60",
            "larger": "60 60",
            "shrink": "-60 -60",
            "smaller": "-60 -60",
            "wider": "80 0",
            "narrower": "-80 0",
            "taller": "0 80",
            "shorter": "0 -80"
        }
        delta_str = deltas.get(d, direction_or_delta)
        if HyprlandIPC.dispatch("resizeactive", delta_str):
            return f"✅ Resized window by {delta_str}."
        return f"❌ Failed to resize window ({direction_or_delta})."

    # ── Grouping & Tabs ───────────────────────────────────────────────

    @staticmethod
    def toggle_group() -> str:
        """Toggles grouping/tabbed mode for active window with adjacent windows."""
        if HyprlandIPC.dispatch("togglegroup"):
            return "✅ Toggled window tabbed group."
        return "❌ Failed to toggle window group."

    @staticmethod
    def cycle_group(direction: str = "f") -> str:
        """Cycles active tab in group ('f' = forward, 'b' = backward)."""
        d = "b" if direction.lower() in {"b", "back", "prev", "previous"} else "f"
        if HyprlandIPC.dispatch("changegroupactive", d):
            return f"✅ Switched to {'next' if d == 'f' else 'previous'} tab in group."
        return "❌ Failed to change tab in group."

    @staticmethod
    def lock_groups(lock: Optional[bool] = None) -> str:
        """Locks or unlocks group switching."""
        arg = "" if lock is None else ("lock" if lock else "unlock")
        if HyprlandIPC.dispatch("lockgroups", arg):
            return f"✅ Window groups {arg or 'toggled'}."
        return "❌ Failed to modify group lock."

    @staticmethod
    def tile_all_windows(ws_id: Optional[int] = None) -> str:
        """Ensures all windows in the active or specified workspace are tiled."""
        if ws_id is None:
            active = WindowManager.get_active_window()
            ws_id = active.get("workspace", {}).get("id") if active else 1

        clients = WindowManager.get_all_windows()
        tiled_count = 0
        for c in clients:
            if c.get("workspace", {}).get("id") == ws_id and c.get("floating"):
                addr = c.get("address", "")
                HyprlandIPC.dispatch("focuswindow", f"address:{addr}")
                HyprlandIPC.dispatch("togglefloating")
                tiled_count += 1

        return f"✅ Tiled {tiled_count} floating window(s) on workspace {ws_id}."

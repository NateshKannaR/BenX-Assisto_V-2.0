"""
Hyprland Monitor Manager - Multi-monitor detection, workspace assignment, and docked profiles.
"""
import logging
from typing import Any, Dict, List, Optional, Union
from jarvis_ai.hyprland.ipc import HyprlandIPC

logger = logging.getLogger(__name__)


class MonitorManager:
    """Manages monitors, resolution detection, workspace binding, and docked profiles."""

    @staticmethod
    def list_monitors() -> List[Dict[str, Any]]:
        """Returns all active connected monitors."""
        return HyprlandIPC.get_monitors()

    @staticmethod
    def get_focused_monitor() -> Optional[Dict[str, Any]]:
        """Returns the monitor currently containing the focused window/cursor."""
        monitors = MonitorManager.list_monitors()
        for m in monitors:
            if m.get("focused"):
                return m
        return monitors[0] if monitors else None

    @staticmethod
    def focus_monitor(target: Union[str, int]) -> str:
        """Focuses a monitor by name (e.g. 'DP-1', 'HDMI-A-1', 'eDP-1') or direction."""
        t = str(target).strip()
        if HyprlandIPC.dispatch("focusmonitor", t):
            return f"✅ Focused monitor '{t}'."
        return f"❌ Failed to focus monitor '{t}'."

    @staticmethod
    def move_workspace_to_monitor(ws: Union[int, str], monitor_name: str) -> str:
        """Assigns / moves a workspace to a specific monitor."""
        arg = f"{ws} {monitor_name}"
        if HyprlandIPC.dispatch("moveworkspacetomonitor", arg):
            return f"✅ Moved workspace {ws} to monitor '{monitor_name}'."
        return f"❌ Failed to move workspace to monitor '{monitor_name}'."

    @staticmethod
    def detect_docked_state() -> str:
        """
        Returns 'docked' if external monitors are present alongside built-in,
        otherwise 'undocked'.
        """
        monitors = MonitorManager.list_monitors()
        if len(monitors) > 1:
            return "docked"
        return "undocked"

    @staticmethod
    def list_monitors_summary() -> str:
        """Human-readable display of connected monitors."""
        monitors = MonitorManager.list_monitors()
        if not monitors:
            return "🖥️ No monitors detected."

        docked = MonitorManager.detect_docked_state()
        lines = [f"🖥️ CONNECTED MONITORS ({len(monitors)} total, State: [bold cyan]{docked.upper()}[/bold cyan]):"]
        for m in monitors:
            name = m.get("name", "?")
            w = m.get("width", 0)
            h = m.get("height", 0)
            rr = round(m.get("refreshRate", 60), 1)
            desc = m.get("description", "")
            ws = m.get("activeWorkspace", {}).get("name", "?")
            focused = " ◀ FOCUSED" if m.get("focused") else ""
            lines.append(f"  • {name} ({desc}) - {w}x{h}@{rr}Hz [Active WS: {ws}]{focused}")
        return "\n".join(lines)

    @staticmethod
    def apply_profile(profile_name: str) -> str:
        """
        Applies monitor configuration profile ('docked' or 'undocked').
        In docked mode: assigns work workspaces 1-5 to external, 6-9 to laptop.
        """
        p = profile_name.lower().strip()
        monitors = MonitorManager.list_monitors()

        if p == "docked":
            if len(monitors) < 2:
                return "⚠️ Only 1 monitor detected. Cannot apply docked multi-monitor profile."
            # Find external monitor (not starting with eDP)
            ext_mon = None
            laptop_mon = None
            for m in monitors:
                name = m.get("name", "")
                if name.startswith("eDP"):
                    laptop_mon = name
                else:
                    ext_mon = name

            ext = ext_mon or monitors[0].get("name")
            laptop = laptop_mon or monitors[-1].get("name")

            # Bind workspaces: 1-5 to external, 6-9 to laptop
            for ws in range(1, 6):
                HyprlandIPC.dispatch("moveworkspacetomonitor", f"{ws} {ext}")
            for ws in range(6, 10):
                HyprlandIPC.dispatch("moveworkspacetomonitor", f"{ws} {laptop}")

            return f"✅ Applied docked profile: WS 1-5 → {ext}, WS 6-9 → {laptop}."

        elif p == "undocked":
            # Consolidate all to primary
            primary = monitors[0].get("name", "eDP-1") if monitors else "eDP-1"
            for ws in range(1, 10):
                HyprlandIPC.dispatch("moveworkspacetomonitor", f"{ws} {primary}")
            return f"✅ Applied undocked profile: all workspaces consolidated on {primary}."

        return f"❌ Unknown profile '{profile_name}'. Use 'docked' or 'undocked'."

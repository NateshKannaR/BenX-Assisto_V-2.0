"""
Workspace Monitor - Hyprland workspace awareness for BenX (Delegates to jarvis_ai.hyprland).
Maintains 100% backward compatibility with all existing callers.
"""
import logging
from typing import Dict, List, Optional
from jarvis_ai.hyprland import (
    HyprlandIPC,
    WindowManager,
    WorkspaceManager,
    MonitorManager,
    PeripheralsManager,
    RulesManager,
)

logger = logging.getLogger(__name__)


def _hyprctl(cmd: str):
    return HyprlandIPC.query(cmd)


def _hyprctl_dispatch(cmd: str) -> bool:
    parts = cmd.split(maxsplit=1)
    dispatcher = parts[0]
    args = parts[1] if len(parts) > 1 else ""
    return HyprlandIPC.dispatch(dispatcher, args)


class WorkspaceMonitor:
    """Full Hyprland workspace state and control - what's open, where, and what's focused."""

    @staticmethod
    def get_all_workspaces() -> List[Dict]:
        return HyprlandIPC.get_workspaces()

    @staticmethod
    def get_all_clients() -> List[Dict]:
        return HyprlandIPC.get_clients()

    @staticmethod
    def get_active_window() -> Optional[Dict]:
        return HyprlandIPC.get_active_window()

    @staticmethod
    def get_active_workspace_id() -> int:
        return WorkspaceManager.get_active_workspace_id()

    @staticmethod
    def get_workspace_map() -> Dict[int, List[Dict]]:
        """Returns {workspace_id: [client, ...]} mapping."""
        clients = HyprlandIPC.get_clients()
        ws_map: Dict[int, List[Dict]] = {}
        for client in clients:
            ws_id = client.get("workspace", {}).get("id", -1)
            ws_map.setdefault(ws_id, []).append(client)
        return ws_map

    @staticmethod
    def full_state_summary() -> str:
        """Human-readable full workspace state for AI context."""
        return WorkspaceManager.full_summary()

    @staticmethod
    def list_workspaces_summary() -> str:
        return WorkspaceManager.full_summary()

    # ── Control methods ──────────────────────────────────────────────

    @staticmethod
    def switch_workspace(ws_id: int) -> str:
        return WorkspaceManager.switch_workspace(ws_id)

    @staticmethod
    def move_window_to_workspace(ws_id: int) -> str:
        return WorkspaceManager.move_window_to_workspace(ws_id)

    @staticmethod
    def focus_window_by_title(title: str) -> str:
        return WindowManager.focus_window(title)

    @staticmethod
    def close_active_window() -> str:
        return WindowManager.close_window()

    @staticmethod
    def toggle_fullscreen() -> str:
        return WindowManager.toggle_fullscreen()

    @staticmethod
    def toggle_float() -> str:
        return WindowManager.toggle_float()

    @staticmethod
    def find_app_workspace(app_name: str) -> str:
        SELF_ALIASES = {"you", "yourself", "benx", "this", "current_app", "self", "this app", "ben"}
        if app_name.lower().strip() in SELF_ALIASES or not app_name.strip():
            app_name = "benx"

        clients = HyprlandIPC.get_clients()
        matches = [
            c for c in clients
            if app_name.lower() in c.get("title", "").lower()
            or app_name.lower() in c.get("class", "").lower()
        ]
        if not matches:
            return f"❌ '{app_name}' is not open in any workspace"
        lines = [f"🔍 '{app_name}' found in:"]
        for c in matches:
            ws_id = c.get("workspace", {}).get("id", "?")
            lines.append(f"  • Workspace {ws_id}: [{c.get('class')}] {c.get('title')}")
        return "\n".join(lines)

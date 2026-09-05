"""
BenX Hyprland Automation Layer - Native Wayland window, workspace, monitor, peripheral & event control.
"""
from jarvis_ai.hyprland.ipc import HyprlandIPC
from jarvis_ai.hyprland.window import WindowManager
from jarvis_ai.hyprland.workspace import WorkspaceManager
from jarvis_ai.hyprland.monitor import MonitorManager
from jarvis_ai.hyprland.event_listener import HyprlandEventListener
from jarvis_ai.hyprland.peripherals import PeripheralsManager
from jarvis_ai.hyprland.rules import RulesManager


class HyprlandManager:
    """Unified façade for all Hyprland capabilities in BenX."""
    ipc = HyprlandIPC
    window = WindowManager
    workspace = WorkspaceManager
    monitor = MonitorManager
    peripherals = PeripheralsManager
    rules = RulesManager
    events = HyprlandEventListener


# Global event listener instance
_listener_instance = None


def get_event_listener() -> HyprlandEventListener:
    global _listener_instance
    if _listener_instance is None:
        _listener_instance = HyprlandEventListener()
    return _listener_instance


__all__ = [
    "HyprlandIPC",
    "WindowManager",
    "WorkspaceManager",
    "MonitorManager",
    "HyprlandEventListener",
    "PeripheralsManager",
    "RulesManager",
    "HyprlandManager",
    "get_event_listener",
]

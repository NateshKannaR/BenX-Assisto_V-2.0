import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Adw, GLib
from typing import Callable, Optional

class ToastManager:
    """Toast notification manager for BenX GTK UI - non-blocking alerts."""
    
    def __init__(self, window: Gtk.Window):
        self.window = window
        self.default_timeout = 3500  # ms
        self.toasts = []
    
    def show(self, title: str, body: str = "", 
             timeout: Optional[int] = None,
             action_label: str = "", action_cb: Optional[Callable] = None,
             priority: str = "normal") -> None:
        """Show toast notification."""
        timeout_ms = timeout or self.default_timeout
        
        toast = Adw.Toast.new(body or title)
        toast.set_title(title)
        toast.set_timeout(timeout_ms)
        toast.set_priority(self._parse_priority(priority))
        
        if action_label and action_cb:
            def on_action():
                action_cb()
                toast.dismiss()
            toast.set_action_name("action")
            toast.set_action_target_value(GLib.Variant("s", action_label))
            toast.connect("activate", lambda *_: on_action())
        
        # Stack toast on top
        Adw.ToastOverlay.add_toast(self.window, toast)
        
        # Auto-dismiss
        GLib.timeout_add(timeout_ms, toast.dismiss)
    
    def success(self, message: str, action_label: str = "Dismiss", timeout: int = 2500) -> None:
        self.show(message, timeout=timeout, action_label=action_label)
    
    def error(self, message: str, action_label: str = "Retry", timeout: int = 4500) -> None:
        self.show(message, priority="high", action_label=action_label)
    
    def info(self, message: str, timeout: int = 3500) -> None:
        self.show(message, timeout=timeout)
    
    def _parse_priority(self, priority: str) -> Adw.ToastPriority:
        prio_map = {
            "low": Adw.ToastPriority.LOW,
            "normal": Adw.ToastPriority.NORMAL,
            "high": Adw.ToastPriority.HIGH,
        }
        return prio_map.get(priority.lower(), Adw.ToastPriority.NORMAL)


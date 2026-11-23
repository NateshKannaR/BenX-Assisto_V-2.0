"""
Hyprland Workspace Manager - Workspace switching, special scratchpads, and layout template management.
"""
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from jarvis_ai.hyprland.ipc import HyprlandIPC

logger = logging.getLogger(__name__)

LAYOUTS_DIR = Path.home() / ".benx" / "layouts"


class WorkspaceManager:
    """Manages workspaces, scratchpads, and persistent layout templates."""

    @staticmethod
    def get_all_workspaces() -> List[Dict[str, Any]]:
        return HyprlandIPC.get_workspaces()

    @staticmethod
    def get_active_workspace_id() -> int:
        aw = HyprlandIPC.get_active_window()
        if aw:
            return aw.get("workspace", {}).get("id", 1)
        workspaces = WorkspaceManager.get_all_workspaces()
        for ws in workspaces:
            if ws.get("hasfullscreen") or ws.get("windows", 0) > 0:
                return ws.get("id", 1)
        return 1

    @staticmethod
    def switch_workspace(ws: Union[int, str]) -> str:
        """Switches active workspace (e.g. 1, 2, 'name:work', 'special:minimized')."""
        target = str(ws).strip()
        if HyprlandIPC.dispatch("workspace", target):
            return f"✅ Switched to workspace {target}."
        return f"❌ Failed to switch to workspace {target}."

    @staticmethod
    def create_or_switch_workspace(name: str) -> str:
        """Creates or switches to a named workspace (e.g. 'dev', 'comms', 'music')."""
        clean_name = name.strip()
        arg = f"name:{clean_name}" if not clean_name.isdigit() else clean_name
        if HyprlandIPC.dispatch("workspace", arg):
            return f"✅ Switched to workspace '{clean_name}'."
        return f"❌ Failed to switch to workspace '{clean_name}'."

    @staticmethod
    def rename_workspace(ws_id: int, new_name: str) -> str:
        """Renames a workspace."""
        if HyprlandIPC.dispatch("renameworkspace", f"{ws_id} {new_name}"):
            return f"✅ Renamed workspace {ws_id} to '{new_name}'."
        return f"❌ Failed to rename workspace {ws_id}."

    @staticmethod
    def move_window_to_workspace(ws: Union[int, str], silent: bool = False) -> str:
        """
        Moves active window to workspace.
        If silent is True, the window moves without switching focus.
        """
        target = str(ws).strip()
        dispatcher = "movetoworkspacesilent" if silent else "movetoworkspace"
        if HyprlandIPC.dispatch(dispatcher, target):
            mode = "silently " if silent else ""
            return f"✅ Window {mode}moved to workspace {target}."
        return f"❌ Failed to move window to workspace {target}."

    @staticmethod
    def move_to_special(special_name: str = "special", silent: bool = False) -> str:
        """Moves active window to a special workspace / scratchpad."""
        name = special_name.strip()
        arg = f"special:{name}" if not name.startswith("special:") else name
        dispatcher = "movetoworkspacesilent" if silent else "movetoworkspace"
        if HyprlandIPC.dispatch(dispatcher, arg):
            return f"✅ Moved window to special workspace '{name}'."
        return f"❌ Failed to move window to special workspace '{name}'."

    @staticmethod
    def toggle_special(special_name: str = "special") -> str:
        """Toggles visibility of a named special scratchpad workspace."""
        name = special_name.strip()
        arg = name if not name.startswith("special:") else name.replace("special:", "")
        if HyprlandIPC.dispatch("togglespecialworkspace", arg):
            return f"✅ Toggled special workspace '{name}'."
        return f"❌ Failed to toggle special workspace '{name}'."

    @staticmethod
    def cycle_workspaces(direction: str = "next") -> str:
        """Cycles to next or previous workspace on current monitor."""
        d = direction.lower().strip()
        arg = "m+1" if d in {"next", "+1", "forward", "f"} else "m-1"
        if HyprlandIPC.dispatch("workspace", arg):
            return f"✅ Cycled to {'next' if arg == 'm+1' else 'previous'} workspace."
        return "❌ Failed to cycle workspace."

    @staticmethod
    def full_summary() -> str:
        """Human-readable full workspace and client summary."""
        workspaces = WorkspaceManager.get_all_workspaces()
        clients = HyprlandIPC.get_clients()
        active_ws_id = WorkspaceManager.get_active_workspace_id()
        active_win = HyprlandIPC.get_active_window()

        ws_map: Dict[Any, List[Dict[str, Any]]] = {}
        for c in clients:
            ws_id = c.get("workspace", {}).get("id", -1)
            ws_map.setdefault(ws_id, []).append(c)

        lines = ["🖥️ HYPRLAND WORKSPACE STATE:"]
        for ws in sorted(workspaces, key=lambda w: (w.get("id", 0) if isinstance(w.get("id"), int) else 999)):
            ws_id = ws.get("id")
            ws_name = ws.get("name", str(ws_id))
            monitor = ws.get("monitor", "?")
            is_active = " ◀ ACTIVE" if ws_id == active_ws_id else ""
            c_list = ws_map.get(ws_id, [])

            lines.append(f"\n  Workspace {ws_name} [{monitor}]{is_active}")
            if c_list:
                for c in c_list:
                    cls = c.get("class", "?")
                    title = c.get("title", "?")[:55]
                    flt = " [floating]" if c.get("floating") else ""
                    fll = " [fullscreen]" if c.get("fullscreen") else ""
                    lines.append(f"    • [{cls}] {title}{flt}{fll}")
            else:
                lines.append("    (empty)")

        if active_win:
            lines.append(
                f"\n🎯 FOCUSED: [{active_win.get('class','?')}] {active_win.get('title','?')} (WS {active_ws_id})"
            )
        return "\n".join(lines)

    # ── Layout Templates (Save / Restore) ──────────────────────────────

    @staticmethod
    def _ensure_layouts_dir():
        LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def save_layout(name: str) -> str:
        """
        Saves current open windows, workspaces, coordinates, sizes, and floating state
        as a layout template JSON file.
        """
        WorkspaceManager._ensure_layouts_dir()
        clean_name = name.strip().lower().replace(" ", "_")
        if not re.fullmatch(r"[\w-]+", clean_name):
            return "❌ Use letters, numbers, spaces, underscores or hyphens in layout names."
        target_file = LAYOUTS_DIR / f"{clean_name}.json"

        clients = HyprlandIPC.query("clients")
        if not isinstance(clients, list):
            return "❌ Could not read windows from Hyprland."
        workspaces = HyprlandIPC.get_workspaces()
        monitors = HyprlandIPC.get_monitors()

        template_data = {
            "name": clean_name,
            "created_at": str(os.environ.get("USER", "benx")),
            "monitors_count": len(monitors),
            "workspaces": [
                {"id": w.get("id"), "name": w.get("name"), "monitor": w.get("monitor")}
                for w in workspaces
            ],
            "windows": [
                {
                    "class": c.get("class"),
                    "title": c.get("title"),
                    "workspace": c.get("workspace", {}).get("id"),
                    "workspace_name": c.get("workspace", {}).get("name"),
                    "floating": c.get("floating", False),
                    "size": c.get("size", [0, 0]),
                    "at": c.get("at", [0, 0]),
                    "fullscreen": c.get("fullscreen", False),
                }
                for c in clients if c.get("class")  # ignore empty dummy clients
            ]
        }

        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=LAYOUTS_DIR, delete=False
            ) as f:
                temporary = Path(f.name)
                json.dump(template_data, f, indent=2)
            temporary.replace(target_file)
            win_count = len(template_data["windows"])
            return f"✅ Saved layout template '{clean_name}' with {win_count} window(s) across {len(workspaces)} workspace(s)."
        except Exception as e:
            return f"❌ Failed to save layout template: {e}"
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @staticmethod
    def restore_layout(name: str) -> str:
        """
        Restores a saved layout template by matching open windows and dispatching
        them to their recorded workspaces and states.
        """
        WorkspaceManager._ensure_layouts_dir()
        clean_name = name.strip().lower().replace(" ", "_")
        if not re.fullmatch(r"[\w-]+", clean_name):
            return "❌ Use letters, numbers, spaces, underscores or hyphens in layout names."
        target_file = LAYOUTS_DIR / f"{clean_name}.json"

        if not target_file.exists():
            return f"❌ Layout template '{clean_name}' not found in {LAYOUTS_DIR}."

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                template = json.load(f)
        except Exception as e:
            return f"❌ Failed to load layout template '{clean_name}': {e}"

        if not isinstance(template, dict) or not isinstance(template.get("windows"), list):
            return "❌ The layout file has an invalid format."
        current_clients = HyprlandIPC.query("clients")
        if not isinstance(current_clients, list):
            return "❌ Could not read windows from Hyprland."

        available = {client["address"]: client for client in current_clients if client.get("address")}
        restored, failed = [], []
        windows = [window for window in template["windows"] if isinstance(window, dict) and window.get("class")]
        matches = []
        # Reserve exact title matches before matching remaining windows by class.
        for exact_title in (True, False):
            unmatched = []
            for window in windows:
                address = next((
                    address for address, client in available.items()
                    if str(client.get("class", "")).casefold() == str(window["class"]).casefold()
                    and (not exact_title or client.get("title") == window.get("title"))
                ), None)
                if address is None:
                    unmatched.append(window)
                else:
                    matches.append((window, address, available.pop(address)))
            windows = unmatched

        missing = [window.get("title") or window["class"] for window in windows]
        for window, address, client in matches:
            label = window.get("title") or window["class"]
            workspace = window.get("workspace_name") or window.get("workspace")
            if isinstance(workspace, str) and not re.fullmatch(r"-?\d+|special:[\w-]+", workspace):
                workspace = f"name:{workspace}"
            moved = workspace is None or HyprlandIPC.dispatch(
                "movetoworkspacesilent", f"{workspace},address:{address}"
            )
            floating = bool(window.get("floating"))
            adjusted = bool(client.get("floating")) == floating or HyprlandIPC.dispatch(
                "setfloating" if floating else "settiled", f"address:{address}"
            )
            (restored if moved and adjusted else failed).append(label)

        summary = [f"Layout '{clean_name}': {len(restored)} window(s) restored."]
        for title, items in (("Restored", restored), ("Missing", missing), ("Failed", failed)):
            if items:
                summary.append(f"{title}: {', '.join(map(str, items))}")
        return "\n".join(summary)

    @staticmethod
    def list_layouts() -> str:
        """Lists all saved layout templates."""
        WorkspaceManager._ensure_layouts_dir()
        files = list(LAYOUTS_DIR.glob("*.json"))
        if not files:
            return "📁 No saved layout templates found. Use 'save this layout as <name>' to create one."

        lines = ["📁 Saved Hyprland Layout Templates:"]
        for f in sorted(files):
            try:
                with open(f, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                wins = len(data.get("windows", []))
                lines.append(f"  • {f.stem} ({wins} windows)")
            except Exception:
                lines.append(f"  • {f.stem}")
        return "\n".join(lines)

    @staticmethod
    def delete_layout(name: str) -> str:
        """Deletes a saved layout template."""
        clean_name = name.strip().lower().replace(" ", "_")
        if not re.fullmatch(r"[\w-]+", clean_name):
            return "❌ Use letters, numbers, spaces, underscores or hyphens in layout names."
        target_file = LAYOUTS_DIR / f"{clean_name}.json"
        if target_file.exists():
            target_file.unlink()
            return f"✅ Deleted layout template '{clean_name}'."
        return f"❌ Layout template '{clean_name}' does not exist."

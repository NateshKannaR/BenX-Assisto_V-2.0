"""
Hyprland IPC Engine - Core communication layer for hyprctl commands and socket operations.
"""
import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class HyprlandIPC:
    """Handles low-level hyprctl JSON queries, dispatches, and socket paths."""

    @staticmethod
    def get_signature() -> str:
        """Returns the active Hyprland instance signature."""
        return os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")

    @staticmethod
    def get_socket2_path() -> Optional[str]:
        """Returns the path to Hyprland's socket2 IPC stream."""
        sig = HyprlandIPC.get_signature()
        runtime = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        if not sig:
            # Try to detect from filesystem if env var is missing
            hypr_dir = os.path.join(runtime, "hypr")
            if os.path.isdir(hypr_dir):
                dirs = sorted(os.listdir(hypr_dir), reverse=True)
                for d in dirs:
                    cand = os.path.join(hypr_dir, d, ".socket2.sock")
                    if os.path.exists(cand):
                        return cand
            return None

        socket_path = os.path.join(runtime, "hypr", sig, ".socket2.sock")
        return socket_path if os.path.exists(socket_path) else None

    @staticmethod
    def is_available() -> bool:
        """Checks if hyprctl is installed and a Hyprland session is reachable."""
        try:
            r = subprocess.run(["hyprctl", "version"], capture_output=True, text=True, timeout=2)
            return r.returncode == 0
        except Exception:
            return False

    @staticmethod
    def query(cmd: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
        """Runs hyprctl <cmd> -j and returns parsed JSON data."""
        try:
            r = subprocess.run(
                ["hyprctl", cmd, "-j"],
                capture_output=True, text=True, timeout=4
            )
            if r.returncode == 0 and r.stdout.strip():
                return json.loads(r.stdout)
            if r.returncode != 0:
                logger.debug(f"hyprctl {cmd} -j failed with code {r.returncode}: {r.stderr.strip()}")
        except Exception as e:
            logger.warning(f"hyprctl query '{cmd}' error: {e}")
        return None

    @staticmethod
    def dispatch(dispatcher: str, args: str = "") -> bool:
        """Runs hyprctl dispatch <dispatcher> <args>."""
        try:
            cmd = ["hyprctl", "dispatch", dispatcher]
            if args:
                cmd.extend(args.split() if isinstance(args, str) else [str(args)])
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
            if r.returncode == 0 and "ok" in r.stdout.lower():
                return True
            # Some dispatchers return 0 with empty stdout or other confirmation
            return r.returncode == 0
        except Exception as e:
            logger.warning(f"hyprctl dispatch '{dispatcher} {args}' error: {e}")
            return False

    @staticmethod
    def batch(dispatches: List[str]) -> bool:
        """Executes multiple hyprctl dispatch commands in batch mode."""
        if not dispatches:
            return True
        try:
            batch_str = " ; ".join(f"dispatch {d}" for d in dispatches)
            r = subprocess.run(
                ["hyprctl", "--batch", batch_str],
                capture_output=True, text=True, timeout=6
            )
            return r.returncode == 0
        except Exception as e:
            logger.warning(f"hyprctl batch error: {e}")
            return False

    @staticmethod
    def get_active_window() -> Optional[Dict[str, Any]]:
        """Returns the currently active window dictionary."""
        data = HyprlandIPC.query("activewindow")
        return data if isinstance(data, dict) and data else None

    @staticmethod
    def get_clients() -> List[Dict[str, Any]]:
        """Returns all open client windows."""
        data = HyprlandIPC.query("clients")
        return data if isinstance(data, list) else []

    @staticmethod
    def get_workspaces() -> List[Dict[str, Any]]:
        """Returns all active workspaces."""
        data = HyprlandIPC.query("workspaces")
        return data if isinstance(data, list) else []

    @staticmethod
    def get_monitors() -> List[Dict[str, Any]]:
        """Returns all connected monitors."""
        data = HyprlandIPC.query("monitors")
        return data if isinstance(data, list) else []

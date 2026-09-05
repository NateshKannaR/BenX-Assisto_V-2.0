"""
BenX Laptop Control - Comprehensive system, power, network, process, package, input & service management.
Wayland-native and Arch Linux optimized with robust confirmation safety barriers.
"""
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ── Safety Protection Sets ───────────────────────────────────────────────────

CRITICAL_PROCESSES = {
    "hyprland", "systemd", "init", "dunst", "mako", "pipewire",
    "wireplumber", "waybar", "dbus-daemon", "polkitd", "sshd",
    "benx", "python", "python3"
}

CRITICAL_SERVICES = {
    "systemd", "dbus", "NetworkManager", "sshd", "polkit", "display-manager", "systemd-logind", "logind"
}


# ── 1. Power Management ──────────────────────────────────────────────────────

class PowerManager:
    """Manages suspend, hibernate, reboot, shutdown, and power profiles."""

    @staticmethod
    def get_battery_info() -> Dict[str, Any]:
        import psutil
        b = psutil.sensors_battery()
        if not b:
            return {"percent": 100, "plugged": True, "secsleft": -1}
        return {
            "percent": round(b.percent, 1),
            "plugged": b.power_plugged,
            "secsleft": b.secsleft
        }

    @staticmethod
    def get_power_profile() -> str:
        """Queries active power profile via powerprofilesctl or sysfs CPU governor."""
        if shutil.which("powerprofilesctl"):
            try:
                r = subprocess.run(["powerprofilesctl", "get"], capture_output=True, text=True, timeout=3)
                if r.returncode == 0:
                    return r.stdout.strip()
            except Exception:
                pass

        # Fallback to sysfs scaling governor
        gov_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
        if gov_path.exists():
            try:
                return f"sysfs governor: {gov_path.read_text().strip()}"
            except Exception:
                pass
        return "balanced (default)"

    @staticmethod
    def set_power_profile(profile: str) -> str:
        """Sets power profile: 'power-saver', 'balanced', or 'performance'."""
        target = profile.lower().strip()
        alias_map = {
            "powersave": "power-saver",
            "battery": "power-saver",
            "eco": "power-saver",
            "save": "power-saver",
            "normal": "balanced",
            "perf": "performance",
            "high": "performance",
            "turbo": "performance"
        }
        target = alias_map.get(target, target)

        if shutil.which("powerprofilesctl"):
            try:
                r = subprocess.run(["powerprofilesctl", "set", target], capture_output=True, text=True, timeout=4)
                if r.returncode == 0:
                    return f"⚡ Power profile set to '{target}'."
                return f"❌ Failed to set power profile: {r.stderr.strip()}"
            except Exception as e:
                return f"❌ powerprofilesctl error: {e}"

        # Fallback to scaling_governor via cpupower or tee
        gov = "powersave" if target == "power-saver" else ("performance" if target == "performance" else "schedutil")
        if shutil.which("cpupower"):
            r = subprocess.run(["sudo", "cpupower", "frequency-set", "-g", gov], capture_output=True, text=True)
            if r.returncode == 0:
                return f"⚡ CPU governor set to '{gov}'."
        return f"⚠️ powerprofilesctl not found. Install via: sudo pacman -S power-profiles-daemon"

    @staticmethod
    def lock() -> str:
        if shutil.which("hyprlock"):
            subprocess.Popen(["hyprlock"])
            return "🔒 Screen locked via hyprlock."
        subprocess.run(["loginctl", "lock-session"])
        return "🔒 Screen locked."

    @staticmethod
    def suspend() -> str:
        r = subprocess.run(["systemctl", "suspend"], capture_output=True, text=True)
        return "💤 System suspended." if r.returncode == 0 else f"❌ Suspend failed: {r.stderr}"

    @staticmethod
    def hibernate() -> str:
        r = subprocess.run(["systemctl", "hibernate"], capture_output=True, text=True)
        return "❄️ System hibernated." if r.returncode == 0 else f"❌ Hibernate failed: {r.stderr}"

    @staticmethod
    def reboot() -> str:
        r = subprocess.run(["systemctl", "reboot"], capture_output=True, text=True)
        return "🔄 Rebooting system..." if r.returncode == 0 else f"❌ Reboot failed: {r.stderr}"

    @staticmethod
    def shutdown() -> str:
        r = subprocess.run(["systemctl", "poweroff"], capture_output=True, text=True)
        return "🔌 Shutting down system..." if r.returncode == 0 else f"❌ Shutdown failed: {r.stderr}"


# ── 2. Network Management (nmcli) ────────────────────────────────────────────

class NetworkManager:
    """Manages Wi-Fi networks, VPN connections, and active interfaces via nmcli."""

    @staticmethod
    def list_wifi() -> str:
        """Lists available Wi-Fi access points."""
        if not shutil.which("nmcli"):
            return "❌ 'nmcli' not found (NetworkManager required)."

        try:
            # Rescan Wi-Fi
            subprocess.run(["nmcli", "device", "wifi", "rescan"], capture_output=True, timeout=5)
            r = subprocess.run(
                ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY,BARS", "device", "wifi", "list"],
                capture_output=True, text=True, timeout=6
            )
            if r.returncode != 0 or not r.stdout.strip():
                return "📶 No Wi-Fi networks found."

            seen = set()
            lines = ["📶 AVAILABLE WI-FI NETWORKS:"]
            for line in r.stdout.strip().splitlines():
                parts = line.split(":")
                if len(parts) < 4:
                    continue
                in_use, ssid, signal, security = parts[0], parts[1], parts[2], parts[3]
                if not ssid or ssid in seen:
                    continue
                seen.add(ssid)
                active_mark = " ◀ CONNECTED" if in_use == "*" else ""
                lines.append(f"  • {ssid} ({signal}%, {security or 'Open'}){active_mark}")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Failed to list Wi-Fi: {e}"

    @staticmethod
    def connect_wifi(ssid: str, password: Optional[str] = None) -> str:
        """Connects to a Wi-Fi network."""
        if not shutil.which("nmcli"):
            return "❌ 'nmcli' not found."

        cmd = ["nmcli", "device", "wifi", "connect", ssid]
        if password:
            cmd.extend(["password", password])

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if r.returncode == 0:
                return f"✅ Successfully connected to Wi-Fi '{ssid}'."
            return f"❌ Connection failed: {r.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return f"⚠️ Connection to '{ssid}' timed out."
        except Exception as e:
            return f"❌ Wi-Fi error: {e}"

    @staticmethod
    def disconnect_wifi() -> str:
        """Disconnects current Wi-Fi connection."""
        try:
            r = subprocess.run(["nmcli", "device", "disconnect", "wlan0"], capture_output=True, text=True, timeout=6)
            if r.returncode == 0:
                return "✅ Disconnected from Wi-Fi."
            # Fallback to generic disconnect
            subprocess.run(["nmcli", "radio", "wifi", "off"], capture_output=True)
            subprocess.run(["nmcli", "radio", "wifi", "on"], capture_output=True)
            return "✅ Wi-Fi radio cycled/disconnected."
        except Exception as e:
            return f"❌ Disconnect failed: {e}"

    @staticmethod
    def forget_wifi(ssid: str) -> str:
        """Deletes saved connection profile for ssid."""
        try:
            r = subprocess.run(["nmcli", "connection", "delete", ssid], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return f"✅ Removed saved network '{ssid}'."
            return f"❌ Could not delete '{ssid}': {r.stderr.strip()}"
        except Exception as e:
            return f"❌ Network forget error: {e}"

    @staticmethod
    def list_vpns() -> str:
        """Lists configured VPN connections."""
        try:
            r = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE,ACTIVE", "connection", "show"],
                capture_output=True, text=True, timeout=4
            )
            vpns = []
            for line in r.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and "vpn" in parts[1].lower():
                    status = "CONNECTED" if parts[2] == "yes" else "DISCONNECTED"
                    vpns.append(f"  • {parts[0]} [{status}]")
            if not vpns:
                return "🔒 No VPN profiles configured."
            return "🔒 VPN PROFILES:\n" + "\n".join(vpns)
        except Exception as e:
            return f"❌ VPN query error: {e}"

    @staticmethod
    def toggle_vpn(vpn_name: Optional[str] = None) -> str:
        """Connects or disconnects a VPN connection."""
        try:
            r = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE,ACTIVE", "connection", "show"],
                capture_output=True, text=True, timeout=4
            )
            target = None
            is_active = False
            for line in r.stdout.splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and "vpn" in parts[1].lower():
                    if not vpn_name or vpn_name.lower() in parts[0].lower():
                        target = parts[0]
                        is_active = (parts[2] == "yes")
                        break

            if not target:
                return f"❌ No VPN matching '{vpn_name or 'any'}' found."

            action = "down" if is_active else "up"
            sub = subprocess.run(["nmcli", "connection", action, target], capture_output=True, text=True, timeout=12)
            if sub.returncode == 0:
                verb = "Disconnected from" if is_active else "Connected to"
                return f"✅ {verb} VPN '{target}'."
            return f"❌ VPN toggle failed: {sub.stderr.strip()}"
        except Exception as e:
            return f"❌ VPN error: {e}"

    @staticmethod
    def connection_info() -> str:
        """Returns primary connection, IP addresses, and gateway."""
        try:
            r = subprocess.run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"], capture_output=True, text=True, timeout=4)
            lines = ["🌐 ACTIVE NETWORK CONNECTIONS:"]
            for line in r.stdout.splitlines():
                p = line.split(":")
                if len(p) >= 4 and p[2] == "connected":
                    lines.append(f"  • {p[0]} ({p[1]}): {p[3]}")

            # IP info
            r_ip = subprocess.run(["ip", "-brief", "address", "show", "up"], capture_output=True, text=True, timeout=3)
            if r_ip.returncode == 0:
                lines.append("\n📌 IP ASSIGNMENTS:")
                for line in r_ip.stdout.splitlines():
                    lines.append(f"  {line}")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Connection info error: {e}"


# ── 3. Process Management ────────────────────────────────────────────────────

class ProcessManager:
    """Monitors running processes, finds resource hogs, and securely terminates tasks."""

    @staticmethod
    def list_top_processes(limit: int = 10, sort_by: str = "cpu") -> str:
        import psutil
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']):
            try:
                info = p.info
                if info['pid'] != 0:
                    procs.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        key = 'cpu_percent' if sort_by == 'cpu' else 'memory_percent'
        procs.sort(key=lambda x: x.get(key) or 0, reverse=True)

        lines = [f"⚙️ TOP {limit} PROCESSES BY {sort_by.upper()}:"]
        for p in procs[:limit]:
            name = p.get('name') or 'unknown'
            pid = p.get('pid')
            cpu = round(p.get('cpu_percent') or 0, 1)
            mem = round(p.get('memory_percent') or 0, 1)
            lines.append(f"  • PID {pid:<6} {name:<22} CPU: {cpu:>4.1f}%  RAM: {mem:>4.1f}%")
        return "\n".join(lines)

    @staticmethod
    def find_processes(query: str) -> List[Dict[str, Any]]:
        import psutil
        matches = []
        q = query.lower().strip()
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
            try:
                name = (p.info.get('name') or '').lower()
                cmdline = ' '.join(p.info.get('cmdline') or []).lower()
                if q in name or q in cmdline:
                    matches.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return matches

    @staticmethod
    def safe_kill(target: Union[str, int]) -> Tuple[bool, str]:
        """
        Terminates a process by PID or name.
        Enforces protection against critical desktop / system services.
        """
        import psutil
        target_str = str(target).lower().strip()
        if target_str in CRITICAL_PROCESSES:
            return False, f"🛑 Blocked: Terminating critical process '{target_str}' is prohibited."

        # If numerical PID
        if target_str.isdigit():
            pid = int(target_str)
            try:
                p = psutil.Process(pid)
                pname = p.name().lower()
                if pname in CRITICAL_PROCESSES or pid in {1, os.getpid()}:
                    return False, f"🛑 Blocked: Terminating critical process '{pname}' (PID {pid}) is prohibited."
                p.terminate()
                p.wait(timeout=3)
                return True, f"✅ Process '{pname}' (PID {pid}) terminated."
            except psutil.NoSuchProcess:
                return False, f"❌ PID {pid} not found."
            except Exception as e:
                return False, f"❌ Kill error: {e}"

        # Otherwise match by name
        matches = ProcessManager.find_processes(target_str)
        if not matches:
            return False, f"❌ No process matching '{target_str}' found."

        killed = []
        for m in matches:
            pname = (m.get('name') or '').lower()
            pid = m.get('pid')
            if pname in CRITICAL_PROCESSES or pid in {1, os.getpid()}:
                continue
            try:
                p = psutil.Process(pid)
                p.terminate()
                killed.append(f"{pname} ({pid})")
            except Exception:
                pass

        if not killed:
            return False, f"🛑 Blocked: Matching processes are protected critical system services."
        return True, f"✅ Terminated: {', '.join(killed)}."


# ── 4. Package Management (pacman / yay / apt) ───────────────────────────────

class PackageManager:
    """Manages package search, updates, and installation across Linux package managers."""

    @staticmethod
    def detect_manager() -> str:
        if shutil.which("yay"):
            return "yay"
        if shutil.which("pacman"):
            return "pacman"
        if shutil.which("apt"):
            return "apt"
        if shutil.which("dnf"):
            return "dnf"
        return "unknown"

    @staticmethod
    def search(query: str) -> str:
        mgr = PackageManager.detect_manager()
        if mgr in {"yay", "pacman"}:
            cmd = [mgr, "-Ss", query]
        elif mgr == "apt":
            cmd = ["apt-cache", "search", query]
        elif mgr == "dnf":
            cmd = ["dnf", "search", query]
        else:
            return "❌ No supported package manager found."

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            lines = r.stdout.strip().splitlines()[:15]
            if not lines:
                return f"📦 No packages matching '{query}' found."
            return f"📦 Search results ({mgr}) for '{query}':\n" + "\n".join(lines)
        except Exception as e:
            return f"❌ Package search error: {e}"

    @staticmethod
    def check_updates() -> str:
        mgr = PackageManager.detect_manager()
        try:
            if mgr == "yay":
                r = subprocess.run(["yay", "-Qu"], capture_output=True, text=True, timeout=15)
            elif mgr == "pacman":
                r = subprocess.run(["checkupdates"], capture_output=True, text=True, timeout=15)
            elif mgr == "apt":
                r = subprocess.run(["apt", "list", "--upgradable"], capture_output=True, text=True, timeout=15)
            else:
                return "❌ Unsupported package manager."

            lines = r.stdout.strip().splitlines()
            if not lines or (len(lines) == 1 and "Listing..." in lines[0]):
                return "✅ System is fully up to date! No pending updates."
            return f"📦 {len(lines)} update(s) available via {mgr}:\n" + "\n".join(lines[:12])
        except Exception as e:
            return f"❌ Update check error: {e}"

    @staticmethod
    def install(pkg: str) -> str:
        mgr = PackageManager.detect_manager()
        cmd = ["sudo", "pacman", "-S", "--noconfirm", pkg] if mgr in {"pacman", "yay"} else ["sudo", "apt-get", "install", "-y", pkg]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                return f"✅ Successfully installed '{pkg}' via {mgr}."
            return f"❌ Installation failed: {r.stderr.strip()[:400]}"
        except Exception as e:
            return f"❌ Install error: {e}"

    @staticmethod
    def update_all() -> str:
        mgr = PackageManager.detect_manager()
        cmd = ["sudo", "pacman", "-Syu", "--noconfirm"] if mgr == "pacman" else (
            ["yay", "-Syu", "--noconfirm"] if mgr == "yay" else ["sudo", "apt-get", "upgrade", "-y"]
        )
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                return f"✅ System upgrade completed successfully via {mgr}."
            return f"❌ System upgrade failed: {r.stderr.strip()[:400]}"
        except Exception as e:
            return f"❌ Upgrade error: {e}"


# ── 5. Input Automation (ydotool - Wayland Safe) ──────────────────────────────

class InputAutomation:
    """Wayland-safe keyboard and mouse automation via ydotool uinput daemon."""

    @staticmethod
    def is_available() -> bool:
        return shutil.which("ydotool") is not None

    @staticmethod
    def click(button: int = 1) -> bool:
        """Sends mouse click (1=left, 2=right, 3=middle)."""
        if not InputAutomation.is_available():
            return False
        # ydotool click 0xC0 (left down+up), 0xC1 (right)
        btn_hex = "0xC0" if button == 1 else ("0xC1" if button == 2 else "0xC2")
        try:
            r = subprocess.run(["ydotool", "click", btn_hex], capture_output=True, timeout=2)
            return r.returncode == 0
        except Exception:
            return False

    @staticmethod
    def move_mouse(x: int, y: int, absolute: bool = False) -> bool:
        """Moves mouse pointer."""
        if not InputAutomation.is_available():
            return False
        cmd = ["ydotool", "mousemove"]
        if absolute:
            cmd.append("-a")
        cmd.extend([str(x), str(y)])
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=2)
            return r.returncode == 0
        except Exception:
            return False

    @staticmethod
    def type_text(text: str) -> bool:
        """Types unicode string using ydotool."""
        if not InputAutomation.is_available() or not text:
            return False
        try:
            r = subprocess.run(["ydotool", "type", text], capture_output=True, timeout=6)
            return r.returncode == 0
        except Exception:
            return False

    @staticmethod
    def press_key(key_str: str) -> bool:
        """Presses a key or key sequence (e.g. 'ctrl+c', 'enter', 'super+space')."""
        if not InputAutomation.is_available():
            return False
        # Can invoke ydotool key or dispatch hyprctl sendshortcut
        try:
            r = subprocess.run(["ydotool", "key", key_str], capture_output=True, timeout=3)
            return r.returncode == 0
        except Exception:
            return False


# ── 6. File Trash & File Management ──────────────────────────────────────────

class FileManager:
    """Safe file operations defaulting to desktop Trash."""

    @staticmethod
    def move_to_trash(path_str: str) -> str:
        """Moves file/directory to desktop trash rather than permanent rm."""
        p = Path(os.path.expanduser(path_str))
        if not p.exists():
            return f"❌ Path does not exist: {path_str}"

        # 1. Try gio trash
        if shutil.which("gio"):
            r = subprocess.run(["gio", "trash", str(p)], capture_output=True, text=True, timeout=4)
            if r.returncode == 0:
                return f"🗑️ Moved '{p.name}' to Trash."

        # 2. Try trash-cli
        if shutil.which("trash-put"):
            r = subprocess.run(["trash-put", str(p)], capture_output=True, text=True, timeout=4)
            if r.returncode == 0:
                return f"🗑️ Moved '{p.name}' to Trash via trash-cli."

        # 3. Fallback: move to ~/.local/share/Trash/files
        trash_dir = Path.home() / ".local" / "share" / "Trash" / "files"
        trash_dir.mkdir(parents=True, exist_ok=True)
        dest = trash_dir / p.name
        shutil.move(str(p), str(dest))
        return f"🗑️ Moved '{p.name}' to {trash_dir}."

    @staticmethod
    def copy_path(src: str, dst: str) -> str:
        s = Path(os.path.expanduser(src))
        d = Path(os.path.expanduser(dst))
        if not s.exists():
            return f"❌ Source not found: {src}"
        try:
            if s.is_dir():
                shutil.copytree(str(s), str(d), dirs_exist_ok=True)
            else:
                shutil.copy2(str(s), str(d))
            return f"✅ Copied '{s.name}' to '{dst}'."
        except Exception as e:
            return f"❌ Copy failed: {e}"

    @staticmethod
    def move_path(src: str, dst: str) -> str:
        s = Path(os.path.expanduser(src))
        d = Path(os.path.expanduser(dst))
        if not s.exists():
            return f"❌ Source not found: {src}"
        try:
            shutil.move(str(s), str(d))
            return f"✅ Moved '{s.name}' to '{dst}'."
        except Exception as e:
            return f"❌ Move failed: {e}"

    @staticmethod
    def rename_path(path_str: str, new_name: str) -> str:
        p = Path(os.path.expanduser(path_str))
        if not p.exists():
            return f"❌ Path not found: {path_str}"
        new_path = p.parent / new_name
        try:
            p.rename(new_path)
            return f"✅ Renamed '{p.name}' to '{new_name}'."
        except Exception as e:
            return f"❌ Rename failed: {e}"


# ── 7. Systemd Service Management ────────────────────────────────────────────

class ServiceManager:
    """Manages system and user systemd units."""

    @staticmethod
    def status(unit: str, user_mode: bool = False) -> str:
        cmd = ["systemctl"]
        if user_mode:
            cmd.append("--user")
        cmd.extend(["status", unit])
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            lines = r.stdout.strip().splitlines()[:8]
            return f"⚙️ Service status ({unit}):\n" + "\n".join(lines)
        except Exception as e:
            return f"❌ Service status error: {e}"

    @staticmethod
    def manage(unit: str, action: str, user_mode: bool = False) -> Tuple[bool, str]:
        """Runs start, stop, restart, enable, disable on a systemd service."""
        act = action.lower().strip()
        if act not in {"start", "stop", "restart", "enable", "disable"}:
            return False, f"❌ Invalid action '{action}'."

        if not user_mode and unit.lower() in CRITICAL_SERVICES and act in {"stop", "disable"}:
            return False, f"🛑 Prohibited: Modifying critical system service '{unit}' is blocked for safety."

        cmd = ["systemctl"]
        if user_mode:
            cmd.append("--user")
        else:
            cmd.insert(0, "sudo")
        cmd.extend([act, unit])

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                mode_str = "user " if user_mode else ""
                return True, f"✅ Service {mode_str}'{unit}' {act}ed successfully."
            return False, f"❌ Failed to {act} {unit}: {r.stderr.strip()}"
        except Exception as e:
            return False, f"❌ Service action error: {e}"

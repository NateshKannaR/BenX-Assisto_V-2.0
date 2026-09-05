#!/usr/bin/env python3
"""
Comprehensive test suite for BenX AI Assistant:
- AI Engine & Config
- Hyprland Automation Layer (IPC, Window, Workspace, Monitor, Peripherals, Rules)
- Laptop Control (Power, Network, Process, Package, Service, File)
- Command Executor Action Dispatch & Confirmation Guards
- UI Components & Vector Assets
"""
import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from jarvis_ai.config import Config
from jarvis_ai.ai_engine import AIEngine
from jarvis_ai.command_engine import CommandEngine
from jarvis_ai.executor import CommandExecutor
from jarvis_ai.hyprland.ipc import HyprlandIPC
from jarvis_ai.hyprland.window import WindowManager
from jarvis_ai.hyprland.workspace import WorkspaceManager
from jarvis_ai.hyprland.monitor import MonitorManager
from jarvis_ai.hyprland.peripherals import PeripheralsManager
from jarvis_ai.hyprland.rules import RulesManager
from jarvis_ai.hyprland import HyprlandManager
from jarvis_ai.laptop_control import (
    PowerManager,
    NetworkManager,
    ProcessManager,
    PackageManager,
    ServiceManager,
    FileManager,
    InputAutomation,
    CRITICAL_PROCESSES,
    CRITICAL_SERVICES,
)


class TestConfigAndEngine(unittest.TestCase):
    def test_config_loaded(self):
        self.assertTrue(hasattr(Config, "MODELS"))
        self.assertGreater(len(Config.MODELS), 0)
        self.assertTrue(hasattr(Config, "GROQ_KEY"))
        self.assertTrue(hasattr(Config, "OPENROUTER_KEY"))

    def test_critical_confirm_actions(self):
        """Ensure destructive operations are protected by confirmation"""
        critical_ops = [
            "shutdown",
            "reboot",
            "suspend",
            "hibernate",
            "process_kill",
            "pkg_install",
            "pkg_update_system",
            "file_trash",
            "service_manage",
            "clipboard_wipe",
            "hypr_delete_layout",
        ]
        for op in critical_ops:
            self.assertIn(op, CommandExecutor.CONFIRM_ACTIONS, f"{op} must be in CONFIRM_ACTIONS")


class TestHyprlandAutomation(unittest.TestCase):
    @patch("jarvis_ai.hyprland.window.WindowManager.find_windows")
    @patch("jarvis_ai.hyprland.ipc.HyprlandIPC.dispatch")
    def test_window_operations(self, mock_dispatch, mock_find):
        mock_dispatch.return_value = True
        mock_find.return_value = [{"address": "0x123", "title": "kitty terminal", "class": "kitty", "workspace": {"id": 1}}]
        wm = WindowManager()

        res_focus = wm.focus_window("kitty")
        self.assertIn("Focused", res_focus)
        mock_dispatch.assert_any_call("focuswindow", "address:0x123")

        res_close = wm.close_window()
        self.assertIn("Closed active window", res_close)
        mock_dispatch.assert_any_call("killactive")

        res_float = wm.toggle_float()
        self.assertIn("Toggled floating state", res_float)
        mock_dispatch.assert_any_call("togglefloating")

        res_pin = wm.toggle_pin()
        self.assertIn("Toggled window pin status", res_pin)
        mock_dispatch.assert_any_call("pin")

        res_move = wm.move_active("r")
        self.assertIn("Moved window", res_move)
        mock_dispatch.assert_any_call("movewindow", "r")

        res_resize = wm.resize_active("50 0")
        self.assertIn("Resized window", res_resize)
        mock_dispatch.assert_any_call("resizeactive", "50 0")

        res_group = wm.toggle_group()
        self.assertIn("Toggled window tabbed group", res_group)
        mock_dispatch.assert_any_call("togglegroup")

        res_cg = wm.cycle_group("f")
        self.assertIn("Switched to next tab in group", res_cg)
        mock_dispatch.assert_any_call("changegroupactive", "f")

    @patch("jarvis_ai.hyprland.ipc.HyprlandIPC.dispatch")
    @patch("jarvis_ai.hyprland.ipc.HyprlandIPC.query")
    def test_workspace_operations(self, mock_query, mock_dispatch):
        mock_dispatch.return_value = True
        mock_query.return_value = [
            {"id": 1, "name": "1", "windows": 2},
            {"id": 2, "name": "2", "windows": 1},
        ]
        wsm = WorkspaceManager()

        res_sw = wsm.switch_workspace(3)
        self.assertIn("Switched to workspace 3", res_sw)
        mock_dispatch.assert_any_call("workspace", "3")

        res_mw = wsm.move_window_to_workspace(2)
        self.assertIn("moved to workspace 2", res_mw)
        mock_dispatch.assert_any_call("movetoworkspace", "2")

        res_ts = wsm.toggle_special("magic")
        self.assertIn("Toggled special workspace 'magic'", res_ts)
        mock_dispatch.assert_any_call("togglespecialworkspace", "magic")

        res_cy = wsm.cycle_workspaces("next")
        self.assertIn("Cycled to next workspace", res_cy)
        mock_dispatch.assert_any_call("workspace", "m+1")

    @patch("jarvis_ai.hyprland.ipc.HyprlandIPC.get_clients")
    @patch("jarvis_ai.hyprland.ipc.HyprlandIPC.get_workspaces")
    @patch("jarvis_ai.hyprland.ipc.HyprlandIPC.get_monitors")
    def test_layout_save_restore(self, mock_mon, mock_ws, mock_clients):
        mock_mon.return_value = [{"id": 0, "name": "eDP-1"}]
        mock_ws.return_value = [{"id": 1, "name": "1", "monitor": "eDP-1"}]
        mock_clients.return_value = [
            {"address": "0x1234", "class": "kitty", "title": "term", "workspace": {"id": 1, "name": "1"}, "floating": False, "size": [800, 600], "at": [100, 100], "fullscreen": False}
        ]
        wsm = WorkspaceManager()
        res = wsm.save_layout("test_test_layout")
        self.assertIn("Saved layout template", res)

        layouts = wsm.list_layouts()
        self.assertIn("test_test_layout", layouts)

        # Cleanup
        del_res = wsm.delete_layout("test_test_layout")
        self.assertIn("Deleted layout", del_res)

    @patch("jarvis_ai.hyprland.ipc.HyprlandIPC.get_monitors")
    def test_monitor_manager(self, mock_mon):
        mock_mon.return_value = [
            {"id": 0, "name": "eDP-1", "width": 1920, "height": 1080, "focused": True, "activeWorkspace": {"id": 1}},
            {"id": 1, "name": "HDMI-A-1", "width": 2560, "height": 1440, "focused": False, "activeWorkspace": {"id": 2}},
        ]
        mm = MonitorManager()
        monitors = mm.list_monitors()
        self.assertEqual(len(monitors), 2)
        self.assertEqual(monitors[0]["name"], "eDP-1")
        self.assertEqual(mm.detect_docked_state(), "docked")

    def test_rules_manager(self):
        rm = RulesManager()
        self.assertTrue(rm.get_rules_path().name == "hyprland_rules.conf")


class TestLaptopControl(unittest.TestCase):
    def test_critical_process_protection(self):
        for proc in ["hyprland", "systemd", "benx", "pipewire", "wireplumber", "sshd"]:
            self.assertIn(proc, CRITICAL_PROCESSES, f"{proc} must be in CRITICAL_PROCESSES")

        pm = ProcessManager()
        ok, msg = pm.safe_kill("hyprland")
        self.assertFalse(ok)
        self.assertIn("blocked", msg.lower())

    def test_critical_service_protection(self):
        for srv in ["systemd", "dbus", "systemd-logind", "sshd"]:
            self.assertIn(srv, CRITICAL_SERVICES, f"{srv} must be in CRITICAL_SERVICES")

        sm = ServiceManager()
        ok, msg = sm.manage("dbus", "stop")
        self.assertFalse(ok)
        self.assertIn("prohibited", msg.lower())

    @patch("shutil.which", return_value="/usr/bin/powerprofilesctl")
    @patch("subprocess.run")
    def test_power_profiles(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="balanced\n")
        pwr = PowerManager()
        profile = pwr.get_power_profile()
        self.assertEqual(profile, "balanced")

    @patch("shutil.which", return_value="/usr/bin/nmcli")
    @patch("subprocess.run")
    def test_network_parsing(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="*:HomeWiFi:80:WPA2:▂▄▆█\n :OfficeWiFi:60:WPA2:▂▄▆_\n"
        )
        nm = NetworkManager()
        networks_str = nm.list_wifi()
        self.assertIn("HomeWiFi", networks_str)
        self.assertIn("80%", networks_str)

    def test_file_manager_paths(self):
        fm = FileManager()
        # Invalid file trash should return error message
        msg = fm.move_to_trash("/tmp/nonexistent_benx_test_file_12345.xyz")
        self.assertIn("Path does not exist", msg)


class TestCommandExecutorRouting(unittest.TestCase):
    @patch("jarvis_ai.command_engine.CommandEngine.hypr_save_layout")
    def test_hypr_save_layout_execution(self, mock_save):
        mock_save.return_value = "Layout 'coding' saved successfully"
        cmd = json.dumps({"command": "hypr_save_layout", "name": "coding"})
        result = CommandExecutor.execute(cmd)
        self.assertIn("coding", result)
        mock_save.assert_called_with("coding")

    @patch("jarvis_ai.command_engine.CommandEngine.power_profile")
    def test_power_profile_execution(self, mock_pwr):
        mock_pwr.return_value = "Active power profile: power-saver"
        cmd = json.dumps({"command": "power_set_profile", "profile": "power-saver"})
        result = CommandExecutor.execute(cmd)
        self.assertIn("power-saver", result)
        mock_pwr.assert_called_with("power-saver")

    @patch("jarvis_ai.command_engine.CommandEngine.wifi_list")
    def test_wifi_scan_execution(self, mock_wifi):
        mock_wifi.return_value = "Available Wi-Fi Networks:\n1. HomeWiFi (80%)"
        cmd = json.dumps({"command": "wifi_scan"})
        result = CommandExecutor.execute(cmd)
        self.assertIn("HomeWiFi", result)
        mock_wifi.assert_called_once()


class TestUIComponents(unittest.TestCase):
    def test_vector_icons_exist(self):
        base_dir = Path(__file__).parent / "jarvis_ai" / "gui" / "assets"
        svg_icon = base_dir / "benx.svg"
        symbolic_icon = base_dir / "benx-symbolic.svg"

        self.assertTrue(svg_icon.exists(), "benx.svg must exist")
        self.assertTrue(symbolic_icon.exists(), "benx-symbolic.svg must exist")
        self.assertGreater(svg_icon.stat().st_size, 100)
        self.assertGreater(symbolic_icon.stat().st_size, 100)

    def test_settings_window_import(self):
        import importlib
        mod = importlib.import_module("jarvis_ai.gui.settings_window")
        self.assertTrue(hasattr(mod, "BenXSettingsWindow"))

    def test_waveform_widget_import(self):
        import importlib
        mod = importlib.import_module("jarvis_ai.gui.waveform_widget")
        self.assertTrue(hasattr(mod, "VoiceWaveformWidget"))


class TestTUIComponents(unittest.TestCase):
    def test_tui_waveform_widget(self):
        from benx_tui import TUIWaveformWidget
        wf = TUIWaveformWidget()
        self.assertEqual(wf.state, "idle")
        wf.set_state("listening")
        self.assertEqual(wf.state, "listening")
        wf.tick()
        wf.set_state("recording")
        wf.tick()
        wf.set_state("thinking")
        wf.tick()

    def test_tui_modals_instantiation(self):
        from benx_tui import TUIConfirmModal, TUISettingsModal, ClipboardModal
        confirm = TUIConfirmModal("Test Title", "Test Message")
        self.assertEqual(confirm.modal_title, "Test Title")
        self.assertEqual(confirm.modal_message, "Test Message")

        settings = TUISettingsModal()
        self.assertIsNotNone(settings)

        clipboard = ClipboardModal()
        self.assertIsNotNone(clipboard)

    def test_tui_app_instantiation(self):
        from benx_tui import BenXTUI
        app = BenXTUI()
        self.assertIsNotNone(app)
        self.assertEqual(app.agent_mode, False)



def run_tests():
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

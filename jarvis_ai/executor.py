"""
Command Executor - Execute parsed commands
"""
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from jarvis_ai.ai_engine import AIEngine
from jarvis_ai.command_engine import CommandEngine
from jarvis_ai.screen_analyzer import ScreenAnalyzer
from jarvis_ai.automation import AutomationEngine
from jarvis_ai.mobile_automation import MobileAutomationEngine
from jarvis_ai.project_orchestrator import ProjectOrchestrator
from jarvis_ai.config import Config
from jarvis_ai.plugin_manager import PluginManager
from jarvis_ai.scheduler import Scheduler
from jarvis_ai.developer_assistant import DeveloperAssistant
from jarvis_ai.dependency_installer import DependencyInstaller

logger = logging.getLogger(__name__)


class CommandExecutor:
    """Execute commands parsed from natural language"""

    _plugin_manager = None
    _scheduler = None
    _developer_assistant = None

    CONFIRM_ACTIONS = {
        "delete_file",
        "file_trash",
        "shutdown",
        "power_shutdown",
        "restart",
        "reboot",
        "power_reboot",
        "suspend",
        "power_suspend",
        "hibernate",
        "power_hibernate",
        "kill_process",
        "process_kill",
        "install_package",
        "pkg_install",
        "update_system",
        "pkg_update_system",
        "move_file",
        "copy_file",
        "file_move",
        "file_copy",
        "service_manage",
        "clipboard_wipe",
        "hypr_delete_layout",
    }

    FILE_ACTIONS = {
        "open_folder",
        "list_files",
        "search_files",
        "read_file",
        "create_file",
        "write_file",
        "delete_file",
        "create_directory",
        "move_file",
        "copy_file",
        "create_pdf",
        "open_file",
    }

    @staticmethod
    def _confirm_action(prompt: str, confirm_cb=None) -> bool:
        if confirm_cb:
            try:
                return bool(confirm_cb(prompt))
            except Exception:
                pass
        try:
            answer = input(f"{prompt} [y/N]: ").strip().lower()
            return answer in {"y", "yes"}
        except Exception:
            return False

    @staticmethod
    def _is_path_allowed(path: str) -> bool:
        if not path:
            return True
        expanded = os.path.realpath(os.path.expanduser(path))
        for root in Config.ALLOWED_ROOTS:
            root_path = os.path.realpath(os.path.expanduser(root))
            if expanded == root_path or expanded.startswith(root_path + os.sep):
                return True
        return False

    @staticmethod
    def _extract_paths(action: str, obj: dict) -> list:
        paths = []
        if action in {"open_folder", "list_files", "read_file", "create_file", "write_file", "delete_file", "create_directory", "open_file"}:
            paths.append(obj.get("path", ""))
        if action in {"search_files"}:
            paths.append(obj.get("path", ""))
        if action in {"move_file", "copy_file"}:
            paths.append(obj.get("path", ""))
            paths.append(obj.get("dest", ""))
        if action in {"create_pdf"}:
            paths.append(obj.get("path", ""))
        return [p for p in paths if p]

    @staticmethod
    def _get_plugin_manager() -> PluginManager:
        if CommandExecutor._plugin_manager is None:
            CommandExecutor._plugin_manager = PluginManager()
            CommandExecutor._plugin_manager.load_plugins()
        return CommandExecutor._plugin_manager

    @staticmethod
    def _get_scheduler() -> Scheduler:
        if CommandExecutor._scheduler is None:
            CommandExecutor._scheduler = Scheduler()
        return CommandExecutor._scheduler

    @staticmethod
    def _get_developer_assistant() -> DeveloperAssistant:
        if CommandExecutor._developer_assistant is None:
            CommandExecutor._developer_assistant = DeveloperAssistant()
        return CommandExecutor._developer_assistant
    
    @staticmethod
    def execute(cmd_json: str, ai_engine: AIEngine = None, user_input: str = "", confirm_cb=None) -> str:
        """Execute a JSON command"""
        try:
            # Parse command first
            obj = json.loads(cmd_json)
            action = obj.get("command", "none")
            # Check if this is a project task
            if ai_engine:
                # Initialize orchestrator if not exists
                if not hasattr(ai_engine, 'project_orchestrator'):
                    ai_engine.project_orchestrator = ProjectOrchestrator(ai_engine)
                
                if ai_engine.project_orchestrator.is_project_task(user_input):
                    logger.info(f"Detected project task: {user_input}")
                    # Get current working directory or project path
                    import os
                    base_path = os.getcwd()
                    result = ai_engine.project_orchestrator.handle_project_request(user_input, base_path)
                    return result
            
            # Apply learned patterns
            if ai_engine and ai_engine.learning_engine:
                learned_cmd = ai_engine.learning_engine.apply_learned_pattern(user_input)
                if learned_cmd:
                    logger.info(f"Using learned pattern for: {user_input}")
                    cmd_json = learned_cmd
            
            obj = json.loads(cmd_json)
            action = obj.get("command", "none")
            
            if action == "none":
                return None  # Question, not command

            plugin_manager = CommandExecutor._get_plugin_manager()
            plugin_handler = plugin_manager.get_handler(action)
            if plugin_handler:
                return plugin_handler(obj, ai_engine, user_input)

            if Config.REQUIRE_CONFIRMATION and action in CommandExecutor.CONFIRM_ACTIONS:
                prompt = f"Confirm action '{action}' for: {user_input}"
                if not CommandExecutor._confirm_action(prompt, confirm_cb=confirm_cb):
                    return "⚠️ Action cancelled."

            if action in CommandExecutor.FILE_ACTIONS:
                paths = CommandExecutor._extract_paths(action, obj)
                if paths and any(not CommandExecutor._is_path_allowed(p) for p in paths):
                    prompt = "This action targets a path outside allowed roots. Continue?"
                    if Config.REQUIRE_CONFIRMATION and not CommandExecutor._confirm_action(prompt, confirm_cb=confirm_cb):
                        return "⚠️ Action cancelled."
            
            # Command mapping
            command_map = {
                # Applications
                "open_app": lambda: CommandEngine.open_app(obj.get("app", "")),
                "list_apps": lambda: CommandEngine.list_running_apps(),
                
                # Audio
                "set_volume": lambda: CommandEngine.set_volume(obj.get("value", 50)),
                "increase_volume": lambda: CommandEngine.increase_volume(obj.get("value", 5)),
                "decrease_volume": lambda: CommandEngine.decrease_volume(obj.get("value", 5)),
                "mute_volume": lambda: CommandEngine.mute_volume(),
                "get_volume": lambda: CommandEngine.get_volume(),
                
                # Brightness
                "set_brightness": lambda: CommandEngine.set_brightness(obj.get("value", 50)),
                "increase_brightness": lambda: CommandEngine.increase_brightness(obj.get("value", 5)),
                "decrease_brightness": lambda: CommandEngine.decrease_brightness(obj.get("value", 5)),
                
                # Files
                "open_folder": lambda: CommandEngine.open_folder(obj.get("path", "~")),
                "list_files": lambda: CommandEngine.list_files(obj.get("path", ".")),
                "search_files": lambda: CommandEngine.search_files(obj.get("query", ""), obj.get("path", ".")),
                "read_file": lambda: CommandEngine.read_file(obj.get("path", ""), obj.get("lines", 50)),
                "create_file": lambda: CommandEngine.create_file(obj.get("path", ""), obj.get("text", "")),
                "write_file": lambda: CommandEngine.write_file(obj.get("path", ""), obj.get("text", "")),
                "delete_file": lambda: CommandEngine.delete_file(obj.get("path", "")),
                "create_directory": lambda: CommandEngine.create_directory(obj.get("path", "")),
                "move_file": lambda: CommandEngine.move_file(obj.get("path", ""), obj.get("dest", "")),
                "copy_file": lambda: CommandEngine.copy_file(obj.get("path", ""), obj.get("dest", "")),
                "create_pdf": lambda: CommandEngine.create_pdf(obj.get("content", obj.get("text", "")), obj.get("path", "")),
                "open_file": lambda: CommandEngine.open_file(obj.get("path", "")),
                
                # Processes
                "kill_process": lambda: CommandEngine.kill_process(obj.get("process", "")),
                "list_processes": lambda: CommandEngine.list_processes(),
                "find_process": lambda: CommandEngine.find_process(obj.get("query", "")),
                
                # System
                "lock_screen": lambda: CommandEngine.lock_screen(),
                "shutdown": lambda: CommandEngine.shutdown(),
                "restart": lambda: CommandEngine.restart(),
                "suspend": lambda: CommandEngine.suspend(),
                "battery": lambda: CommandEngine.battery(),
                "system_info": lambda: CommandEngine.system_info(),
                "disk_usage": lambda: CommandEngine.disk_usage(obj.get("path", "/")),
                
                # Network
                "connect_wifi": lambda: CommandEngine.connect_wifi(obj.get("ssid", "")),
                "list_wifi": lambda: CommandEngine.list_wifi(),
                "network_status": lambda: CommandEngine.network_status(),
                
                # Media
                "play_music": lambda: CommandEngine.play_music(),
                "pause_music": lambda: CommandEngine.pause_music(),
                "next_track": lambda: CommandEngine.next_track(),
                "previous_track": lambda: CommandEngine.previous_track(),
                "get_media_info": lambda: CommandEngine.get_media_info(),
                
                # Utilities
                "get_clipboard": lambda: CommandEngine.get_clipboard(),
                "set_clipboard": lambda: CommandEngine.set_clipboard(obj.get("text", "")),
                "get_weather": lambda: CommandEngine.get_weather(obj.get("city", "")),
                "open_url": lambda: CommandEngine.open_url(obj.get("url", "")),
                "take_screenshot": lambda: CommandEngine.take_screenshot(),
                "analyze_screen": lambda: CommandExecutor._analyze_screen_with_ai(ai_engine),
                "analyze_image": lambda: CommandExecutor._analyze_image(ai_engine, obj.get("path", "")),
                "read_screen_text": lambda: CommandEngine.read_screen_text(),
                "automate": lambda: CommandExecutor._execute_automation(obj.get("instruction", user_input), ai_engine),
                "preview_automation": lambda: CommandExecutor._preview_automation(obj.get("instruction", user_input), ai_engine),
                "pause_automation": lambda: CommandExecutor._pause_automation(ai_engine),
                "resume_automation": lambda: CommandExecutor._resume_automation(ai_engine),
                "screen_aware_click": lambda: CommandExecutor._screen_aware_click(obj.get("text", obj.get("query", obj.get("name", ""))), ai_engine),
                "mobile_automate": lambda: CommandExecutor._mobile_automate(obj.get("instruction", user_input), ai_engine),
                "mobile_tap": lambda: CommandExecutor._mobile_tap(obj.get("text", obj.get("x", None), obj.get("y", None)), ai_engine),
                "mobile_screenshot": lambda: CommandExecutor._mobile_screenshot(ai_engine),
                "mobile_ocr": lambda: CommandExecutor._mobile_ocr(ai_engine),
                "mobile_apps": lambda: CommandExecutor._mobile_apps(ai_engine),
                "search_github": lambda: CommandEngine.search_github(obj.get("query", "")),
                "open_whatsapp_contact": lambda: CommandEngine.open_whatsapp_contact(obj.get("contact", "")),
                "send_whatsapp_message": lambda: CommandEngine.send_whatsapp_message(
                    obj.get("contact", ""),
                    obj.get("message", obj.get("text", "")),
                ),
                "schedule_task": lambda: CommandExecutor._schedule_task(obj, user_input, ai_engine),
                "list_scheduled_tasks": lambda: CommandExecutor._list_scheduled_tasks(),
                "cancel_scheduled_task": lambda: CommandExecutor._cancel_scheduled_task(obj.get("name", obj.get("text", ""))),
                
                # Project Orchestration
                "create_project": lambda: CommandExecutor._handle_project_task(ai_engine, user_input, obj.get("path", ".")),
                "modify_project": lambda: CommandExecutor._handle_project_task(ai_engine, user_input, obj.get("path", ".")),
                "refactor_project": lambda: CommandExecutor._handle_project_task(ai_engine, user_input, obj.get("path", ".")),
                "fix_project_bug": lambda: CommandExecutor._handle_project_task(ai_engine, user_input, obj.get("path", ".")),

                # Developer Assistance
                "analyze_project": lambda: CommandExecutor._analyze_project(obj, user_input),
                "search_code": lambda: CommandExecutor._search_code(obj),
                "find_symbol": lambda: CommandExecutor._find_symbol(obj),
                "list_todos": lambda: CommandExecutor._list_todos(obj),
                "find_dead_code": lambda: CommandExecutor._find_dead_code(obj),
                "generate_snippet": lambda: CommandExecutor._generate_snippet(obj),
                "remember_developer_note": lambda: CommandExecutor._remember_developer_note(obj, user_input),
                "recall_developer_memory": lambda: CommandExecutor._recall_developer_memory(obj),
                
                # Packages
                "install_package": lambda: CommandEngine.install_package(obj.get("package", "")),
                "install_python_package": lambda: CommandEngine.install_python_package(obj.get("package", "")),
                "update_system": lambda: CommandEngine.update_system(),
                "check_updates": lambda: CommandEngine.check_updates(),
                # Full Shell Control (Step 1)
                "shell_execute": lambda: CommandEngine.shell_execute(obj.get("cmd", ""), sudo=obj.get("sudo", False)),
                "sudo_execute": lambda: CommandEngine.shell_execute(obj.get("cmd", ""), sudo=True),
                # BLACKBOXAI Tools
                "read_file": lambda: CommandEngine.read_file(obj.get("path", "")),
                "list_files": lambda: CommandEngine.list_files(obj.get("path", ".")),
                "search_files": lambda: CommandEngine.search_files(obj.get("path", "."), obj.get("query", "")),
                "create_file": lambda: CommandEngine.create_file(obj.get("path", ""), obj.get("content", "")),
                "edit_file": lambda: CommandEngine.edit_file(obj.get("path", ""), obj.get("old_str", ""), obj.get("new_str", "")),

                # Workspace / Window Management (Hyprland)
                "list_workspaces": lambda: CommandEngine.list_workspaces(),
                "switch_workspace": lambda: CommandEngine.switch_workspace(int(obj.get("value", 1))),
                "move_to_workspace": lambda: CommandEngine.move_to_workspace(int(obj.get("value", 1))),
                "focus_window": lambda: CommandEngine.focus_window(obj.get("app", obj.get("query", ""))),
                "find_app_workspace": lambda: CommandEngine.find_app_workspace(obj.get("app", obj.get("query", ""))),
                "close_active_window": lambda: CommandEngine.close_active_window(),
                "toggle_fullscreen": lambda: CommandEngine.toggle_fullscreen(),
                "toggle_float": lambda: CommandEngine.toggle_float(),

                # Extended Hyprland Actions
                "hypr_move_window": lambda: CommandEngine.hypr_move_window(obj.get("direction", obj.get("text", "right"))),
                "hypr_resize_window": lambda: CommandEngine.hypr_resize_window(obj.get("delta", obj.get("text", "grow"))),
                "hypr_tile_all": lambda: CommandEngine.hypr_tile_all(obj.get("workspace")),
                "hypr_toggle_pin": lambda: CommandEngine.hypr_toggle_pin(obj.get("app", obj.get("query"))),
                "hypr_toggle_group": lambda: CommandEngine.hypr_toggle_group(),
                "hypr_cycle_group": lambda: CommandEngine.hypr_cycle_group(obj.get("direction", "f")),
                "hypr_lock_groups": lambda: CommandEngine.hypr_lock_groups(),
                "hypr_save_layout": lambda: CommandEngine.hypr_save_layout(obj.get("name", obj.get("text", "default"))),
                "hypr_restore_layout": lambda: CommandEngine.hypr_restore_layout(obj.get("name", obj.get("text", "default"))),
                "hypr_list_layouts": lambda: CommandEngine.hypr_list_layouts(),
                "hypr_delete_layout": lambda: CommandEngine.hypr_delete_layout(obj.get("name", obj.get("text", ""))),
                "hypr_cycle_workspaces": lambda: CommandEngine.hypr_cycle_workspaces(obj.get("direction", "next")),
                "hypr_move_to_special": lambda: CommandEngine.hypr_move_to_special(obj.get("name", "special"), silent=obj.get("silent", False)),
                "hypr_toggle_special": lambda: CommandEngine.hypr_toggle_special(obj.get("name", "special")),
                "hypr_list_monitors": lambda: CommandEngine.hypr_list_monitors(),
                "hypr_apply_monitor_profile": lambda: CommandEngine.hypr_apply_monitor_profile(obj.get("profile", "docked")),
                "hypr_screenshot_fullscreen": lambda: CommandEngine.hypr_screenshot_fullscreen(obj.get("path")),
                "hypr_screenshot_region": lambda: CommandEngine.hypr_screenshot_region(obj.get("path")),
                "hypr_screenshot_window": lambda: CommandEngine.hypr_screenshot_window(obj.get("path")),
                "hypr_start_recording": lambda: CommandEngine.hypr_start_recording(audio=obj.get("audio", False)),
                "hypr_stop_recording": lambda: CommandEngine.hypr_stop_recording(),
                "hypr_clipboard_history": lambda: CommandEngine.hypr_clipboard_history(int(obj.get("value", 15))),
                "hypr_clipboard_search": lambda: CommandEngine.hypr_clipboard_search(obj.get("query", obj.get("text", ""))),
                "hypr_clipboard_paste": lambda: CommandEngine.hypr_clipboard_paste(str(obj.get("value", obj.get("text", "0")))),
                "hypr_add_window_rule": lambda: CommandEngine.hypr_add_window_rule(
                    obj.get("rule", "float on"),
                    obj.get("target", obj.get("app", "")),
                    obj.get("match_type", "title")
                ),
                "hypr_remove_window_rule": lambda: CommandEngine.hypr_remove_window_rule(obj.get("target", obj.get("query", ""))),

                # Laptop Control
                "power_profile": lambda: CommandEngine.power_profile(obj.get("profile")),
                "power_set_profile": lambda: CommandEngine.power_profile(obj.get("profile")),
                "power_suspend": lambda: CommandEngine.suspend(),
                "power_hibernate": lambda: CommandEngine.power_hibernate(),
                "power_reboot": lambda: CommandEngine.restart(),
                "power_shutdown": lambda: CommandEngine.shutdown(),
                "wifi_list": lambda: CommandEngine.wifi_list(),
                "wifi_scan": lambda: CommandEngine.wifi_list(),
                "wifi_connect": lambda: CommandEngine.wifi_connect(obj.get("ssid", ""), obj.get("password")),
                "wifi_disconnect": lambda: CommandEngine.wifi_disconnect(),
                "wifi_forget": lambda: CommandEngine.wifi_forget(obj.get("ssid", "")),
                "vpn_list": lambda: CommandEngine.vpn_list(),
                "vpn_toggle": lambda: CommandEngine.vpn_toggle(obj.get("name")),
                "network_info": lambda: CommandEngine.network_info(),
                "process_top": lambda: CommandEngine.process_top(int(obj.get("value", 10)), obj.get("sort_by", "cpu")),
                "process_kill": lambda: CommandEngine.process_kill(obj.get("process", obj.get("query", obj.get("value", "")))),
                "pkg_search": lambda: CommandEngine.pkg_search(obj.get("package", obj.get("query", ""))),
                "pkg_check_updates": lambda: CommandEngine.pkg_check_updates(),
                "pkg_install": lambda: CommandEngine.pkg_install(obj.get("package", "")),
                "pkg_update_system": lambda: CommandEngine.pkg_update_system(),
                "input_click": lambda: CommandEngine.input_click(int(obj.get("value", 1))),
                "input_type": lambda: CommandEngine.input_type(obj.get("text", "")),
                "file_trash": lambda: CommandEngine.file_trash(obj.get("path", "")),
                "file_move": lambda: CommandEngine.file_move(obj.get("path", ""), obj.get("dest", "")),
                "file_copy": lambda: CommandEngine.file_copy(obj.get("path", ""), obj.get("dest", "")),
                "file_rename": lambda: CommandEngine.file_rename(obj.get("path", ""), obj.get("name", obj.get("dest", ""))),
                "service_status": lambda: CommandEngine.service_status(obj.get("service", obj.get("name", "")), user_mode=obj.get("user", False)),
                "service_manage": lambda: CommandEngine.service_manage(
                    obj.get("service", obj.get("name", "")),
                    obj.get("action", "status"),
                    user_mode=obj.get("user", False)
                ),

                # Bluetooth
                "bluetooth_list_paired": lambda: CommandEngine.bluetooth_list_paired(),
                "bluetooth_list_available": lambda: CommandEngine.bluetooth_list_available(),
                "bluetooth_connect": lambda: CommandEngine.bluetooth_connect(obj.get("device", obj.get("query", ""))),
                "bluetooth_disconnect": lambda: CommandEngine.bluetooth_disconnect(obj.get("device", obj.get("query", ""))),
                "bluetooth_pair": lambda: CommandEngine.bluetooth_pair(obj.get("device", obj.get("query", ""))),
                "bluetooth_status": lambda: CommandEngine.bluetooth_status(),
                "bluetooth_on": lambda: CommandEngine.bluetooth_power(True),
                "bluetooth_off": lambda: CommandEngine.bluetooth_power(False),

                # Notifications
                "send_notification": lambda: CommandEngine.send_notification(
                    obj.get("title", obj.get("text", "BenX")),
                    obj.get("body", obj.get("message", "")),
                    obj.get("urgency", "normal")
                ),

                # Email
                "email_inbox": lambda: CommandEngine.email_read_inbox(int(obj.get("value", 5))),
                "email_read": lambda: CommandEngine.email_read_body(int(obj.get("value", 1))),
                "email_send": lambda: CommandEngine.email_send(
                    obj.get("to", obj.get("contact", "")),
                    obj.get("subject", obj.get("title", "")),
                    obj.get("body", obj.get("text", obj.get("message", "")))
                ),
                "email_search": lambda: CommandEngine.email_search(obj.get("query", "")),

                # Phone calls
                "make_call": lambda: CommandExecutor._make_call(obj.get("contact", obj.get("query", obj.get("text", ""))), ai_engine),
                "hangup_call": lambda: CommandExecutor._hangup_call(),

                # Browser Automation
                "browser_open": lambda: CommandEngine.browser_open(obj.get("url", ""), obj.get("workspace")),
                "browser_list_tabs": lambda: CommandEngine.browser_list_tabs(obj.get("workspace")),
                "browser_switch_tab": lambda: CommandEngine.browser_switch_tab(obj.get("query", obj.get("tab", "")), obj.get("workspace")),
                "browser_scrape": lambda: CommandEngine.browser_scrape(obj.get("url", ""), obj.get("query", "body")),
                "browser_screenshot": lambda: CommandEngine.browser_screenshot(obj.get("url", "")),
                "browser_search": lambda: CommandEngine.browser_search(obj.get("query", "")),
                "type_in_ws_terminal": lambda: CommandEngine.type_in_ws_terminal(obj.get("workspace", 1), obj.get("text", "")),
                "type_in_active_window": lambda: CommandEngine.type_in_active_window(obj.get("text", "")),
                "type_in_app": lambda: CommandEngine.type_in_app(obj.get("app", ""), obj.get("text", "")),
                # New enhanced automation
                "run_script":   lambda: CommandEngine.run_script(obj.get("path", "")),
                "watch_file":   lambda: CommandEngine.watch_file(obj.get("path", ""), int(obj.get("duration", 10))),
                "notify_when":  lambda: CommandEngine.notify_when(obj.get("cmd", ""), obj.get("message", ""), int(obj.get("interval", 5)), int(obj.get("timeout", 60))),
            }
            
            if action in command_map:
                try:
                    result = command_map[action]()
                except (ImportError, ModuleNotFoundError) as import_error:
                    # Dependency missing - try to install
                    logger.info(f"Dependency missing for {action}: {str(import_error)}")
                    install_result = DependencyInstaller.auto_install_for_command(action, confirm_cb)
                    if install_result:
                        if "cancelled" in install_result.lower():
                            return install_result
                        # Retry the command after installation
                        try:
                            result = command_map[action]()
                        except Exception as retry_error:
                            return f"❌ Command failed even after installing dependencies: {str(retry_error)}"
                    else:
                        return f"❌ {str(import_error)}"
                except Exception as cmd_error:
                    # Check if error message indicates missing dependencies
                    error_str = str(cmd_error).lower()
                    if any(keyword in error_str for keyword in ["no module", "not available", "not installed", "install:"]):
                        logger.info(f"Possible dependency issue for {action}: {str(cmd_error)}")
                        install_result = DependencyInstaller.auto_install_for_command(action, confirm_cb)
                        if install_result:
                            if "cancelled" in install_result.lower():
                                return install_result
                            # Retry the command after installation
                            try:
                                result = command_map[action]()
                            except Exception as retry_error:
                                return f"❌ Command failed even after installing dependencies: {str(retry_error)}"
                        else:
                            raise cmd_error
                    else:
                        raise cmd_error
                
                # Self-reflect and learn
                if ai_engine and ai_engine.learning_engine:
                    corrected = ai_engine.learning_engine.self_reflect(user_input, action, result)
                    if corrected:
                        try:
                            corrected_obj = json.loads(corrected)
                            corrected_action = corrected_obj.get("command", "")
                            if corrected_action in command_map:
                                logger.info(f"Retrying with learned correction")
                                result = command_map[corrected_action]()
                        except Exception:
                            pass
                
                return result
            else:
                error_msg = f"❌ Unknown command: {action}"
                if ai_engine and ai_engine.learning_engine:
                    ai_engine.learning_engine.learn_from_failure(user_input, action, error_msg)
                return error_msg
                
        except json.JSONDecodeError:
            return None  # Treat as question if JSON parsing fails
        except Exception as e:
            logger.error(f"Command execution error: {e}")
            error_msg = f"❌ Execution error: {str(e)}"
            if ai_engine and ai_engine.learning_engine:
                ai_engine.learning_engine.learn_from_failure(user_input, "unknown", error_msg, str(e))
            return error_msg
    
    @staticmethod
    def _analyze_screen_with_ai(ai_engine: AIEngine) -> str:
        """Analyze screen with AI vision"""
        try:
            from PIL import Image
            import pyautogui
        except ImportError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else "required packages"
            raise ImportError(f"Screen analysis requires: pyautogui, pytesseract, Pillow. Missing: {missing}")

        from jarvis_ai.command_engine import CommandEngine
        result = CommandEngine.take_screenshot()  # already hides BenX window
        if "❌" in result:
            return result

        try:
            img = Image.open(CommandExecutor._get_screenshot_path())
            screen_width, screen_height = pyautogui.size()

            try:
                import pytesseract, os
                if 'TESSDATA_PREFIX' not in os.environ:
                    os.environ['TESSDATA_PREFIX'] = '/usr/share/tessdata/'
                ocr_text = pytesseract.image_to_string(img)
            except ImportError:
                raise ImportError("Screen analysis requires pytesseract. Install: pip install pytesseract")
            except Exception as ocr_error:
                error_msg = str(ocr_error)
                if 'eng.traineddata' in error_msg or 'tessdata' in error_msg:
                    ocr_text = "OCR Error: run ./install_tesseract_eng.sh to install language data"
                else:
                    ocr_text = f"OCR failed: {error_msg}"

            # Use AI vision if available, else fall back to formatted OCR
            if ai_engine:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    img.save(tmp.name)
                    tmp_path = tmp.name
                try:
                    vision = ai_engine.analyze_image(
                        tmp_path,
                        f"Analyze this screenshot. Describe what applications, windows, and content are visible. "
                        f"OCR also found this text: {ocr_text[:500]}"
                    )
                    return f"📸 Screen Analysis:\n\n{vision}\n\n📝 OCR Text (raw):\n{ocr_text[:800]}"
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

            return CommandExecutor._format_screen_analysis(screen_width, screen_height, ocr_text, img)

        except ImportError:
            raise
        except Exception as e:
            return f"❌ Screen analysis error: {str(e)}"
    
    @staticmethod
    def _format_screen_analysis(width: int, height: int, ocr_text: str, image) -> str:
        """Format screen analysis in a beautiful, readable way"""
        import re
        
        # Clean up OCR text
        lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]
        
        # Detect content types
        urls = []
        times = []
        phone_numbers = []
        emails = []
        file_names = []
        messages = []
        other_text = []
        
        url_pattern = r'https?://[^\s]+|www\.[^\s]+|[a-z]+\.[a-z]+\.[a-z]+/[^\s]*'
        time_pattern = r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b'
        phone_pattern = r'\+?\d[\d\s-]{8,}'
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        file_pattern = r'[\w-]+\.(?:pdf|doc|docx|txt|png|jpg|jpeg|gif|zip|rar|mp4|mp3)'
        
        for line in lines:
            # Check for URLs
            if re.search(url_pattern, line, re.IGNORECASE):
                url_matches = re.findall(url_pattern, line, re.IGNORECASE)
                urls.extend(url_matches)
            
            # Check for times
            time_matches = re.findall(time_pattern, line)
            if time_matches:
                times.extend(time_matches)
            
            # Check for phone numbers
            phone_matches = re.findall(phone_pattern, line)
            if phone_matches:
                phone_numbers.extend([p.strip() for p in phone_matches if len(p.replace(' ', '').replace('-', '')) >= 10])
            
            # Check for emails
            email_matches = re.findall(email_pattern, line)
            if email_matches:
                emails.extend(email_matches)
            
            # Check for file names
            file_matches = re.findall(file_pattern, line, re.IGNORECASE)
            if file_matches:
                file_names.extend(file_matches)
            
            # Categorize remaining text
            if len(line) > 10 and not any(re.search(p, line) for p in [url_pattern, file_pattern]):
                if ':' in line and len(line) < 100:
                    messages.append(line)
                else:
                    other_text.append(line)
        
        # Build beautiful formatted output
        output = []
        output.append("╔═══════════════════════════════════════════════════════════╗")
        output.append("║           📸 SCREEN ANALYSIS REPORT                       ║")
        output.append("╚═══════════════════════════════════════════════════════════╝")
        output.append("")
        output.append(f"📐 Screen Resolution: {width} × {height}")
        output.append(f"📊 Total Text Elements: {len(lines)}")
        output.append("")
        
        # URLs
        if urls:
            output.append("🔗 LINKS DETECTED:")
            output.append("─" * 60)
            for i, url in enumerate(set(urls), 1):
                output.append(f"  {i}. {url}")
            output.append("")
        
        # Files
        if file_names:
            output.append("📄 FILES DETECTED:")
            output.append("─" * 60)
            for i, file in enumerate(set(file_names), 1):
                output.append(f"  {i}. {file}")
            output.append("")
        
        # Phone numbers
        if phone_numbers:
            output.append("📱 PHONE NUMBERS:")
            output.append("─" * 60)
            for i, phone in enumerate(set(phone_numbers), 1):
                output.append(f"  {i}. {phone}")
            output.append("")
        
        # Emails
        if emails:
            output.append("📧 EMAIL ADDRESSES:")
            output.append("─" * 60)
            for i, email in enumerate(set(emails), 1):
                output.append(f"  {i}. {email}")
            output.append("")
        
        # Messages/Chat
        if messages:
            output.append("💬 MESSAGES/CHAT:")
            output.append("─" * 60)
            for msg in messages[:10]:  # Limit to 10 messages
                output.append(f"  • {msg}")
            if len(messages) > 10:
                output.append(f"  ... and {len(messages) - 10} more messages")
            output.append("")
        
        # Other important text
        if other_text:
            output.append("📝 OTHER TEXT:")
            output.append("─" * 60)
            for text in other_text[:15]:  # Limit to 15 items
                if len(text) > 60:
                    output.append(f"  • {text[:57]}...")
                else:
                    output.append(f"  • {text}")
            if len(other_text) > 15:
                output.append(f"  ... and {len(other_text) - 15} more items")
            output.append("")
        
        output.append("─" * 60)
        output.append("✨ Analysis complete! Use the copy button to save this report.")
        
        return "\n".join(output)
    
    @staticmethod
    def _analyze_image(ai_engine: AIEngine, image_path: str) -> str:
        """Analyze an image file"""
        if not ai_engine:
            return "❌ AI engine required for image analysis"
        
        if not image_path:
            return "❌ No image path specified"
        
        import os
        path = os.path.expanduser(image_path)
        if not os.path.exists(path):
            return f"❌ Image not found: {path}"
        
        return ai_engine.analyze_image(path, "What is in this image? Describe it in detail.")
    
    @staticmethod
    def _execute_automation(instruction: str, ai_engine: AIEngine) -> str:
        """Execute automation"""
        if not ai_engine:
            return "❌ AI engine required for automation"
        
        try:
            automation_engine = CommandExecutor._get_automation_engine(ai_engine)
            return automation_engine.automate(instruction)
        except ImportError as e:
            raise ImportError(f"Automation not available. Missing: {str(e)}")

    @staticmethod
    def _preview_automation(instruction: str, ai_engine: AIEngine) -> str:
        if not ai_engine:
            return "❌ AI engine required for automation"
        automation_engine = CommandExecutor._get_automation_engine(ai_engine)
        plan = automation_engine.understand_automation(instruction)
        return automation_engine.preview_automation(plan)

    @staticmethod
    def _pause_automation(ai_engine: AIEngine) -> str:
        if not ai_engine:
            return "❌ AI engine required for automation"
        return CommandExecutor._get_automation_engine(ai_engine).pause()

    @staticmethod
    def _resume_automation(ai_engine: AIEngine) -> str:
        if not ai_engine:
            return "❌ AI engine required for automation"
        return CommandExecutor._get_automation_engine(ai_engine).resume()

    @staticmethod
    def _screen_aware_click(target: str, ai_engine: AIEngine) -> str:
        if not ai_engine:
            return "❌ AI engine required for automation"
        try:
            return CommandExecutor._get_automation_engine(ai_engine).screen_aware_click(target)
        except ImportError as e:
            raise ImportError(f"Screen automation not available. Missing: {str(e)}")
    
    @staticmethod
    def _get_screenshot_path() -> str:
        from jarvis_ai.config import Config
        return Config.SCREENSHOT_PATH

    @staticmethod
    def _get_automation_engine(ai_engine: AIEngine) -> AutomationEngine:
        if not hasattr(ai_engine, "automation_engine"):
            ai_engine.automation_engine = AutomationEngine(ai_engine)
        return ai_engine.automation_engine

    @staticmethod
    def _get_mobile_engine(ai_engine: AIEngine) -> 'MobileAutomationEngine':
        if not hasattr(ai_engine, "mobile_engine"):
            ai_engine.mobile_engine = MobileAutomationEngine(ai_engine)
        return ai_engine.mobile_engine

    @staticmethod
    def _mobile_automate(instruction: str, ai_engine: AIEngine) -> str:
        if not ai_engine:
            return "❌ AI engine required"
        try:
            mobile_eng = CommandExecutor._get_mobile_engine(ai_engine)
            return mobile_eng.automate(instruction)
        except Exception as e:
            return f"❌ Mobile automation error: {str(e)}. Run 'adb devices' & connect phone."

    @staticmethod
    def _mobile_tap(text: str = None, x: int = None, y: int = None, ai_engine: AIEngine = None) -> str:
        if not ai_engine:
            return "❌ AI engine required"
        try:
            mobile_eng = CommandExecutor._get_mobile_engine(ai_engine)
            if not mobile_eng.device:
                mobile_eng.connect()
            if text:
                return mobile_eng.tap(text=text)
            elif x and y:
                return mobile_eng.tap(x=x, y=y)
            return "❌ Specify text or x,y"
        except Exception as e:
            return f"❌ Mobile tap failed: {str(e)}"

    @staticmethod
    def _mobile_screenshot(ai_engine: AIEngine = None) -> str:
        if not ai_engine:
            return "❌ AI engine required"
        try:
            mobile_eng = CommandExecutor._get_mobile_engine(ai_engine)
            if not mobile_eng.device:
                mobile_eng.connect()
            return mobile_eng.screenshot()
        except Exception as e:
            return f"❌ Mobile screenshot failed: {str(e)}"

    @staticmethod
    def _mobile_ocr(ai_engine: AIEngine = None) -> str:
        if not ai_engine:
            return "❌ AI engine required"
        try:
            mobile_eng = CommandExecutor._get_mobile_engine(ai_engine)
            if not mobile_eng.device:
                mobile_eng.connect()
            return mobile_eng.ocr_screen()
        except Exception as e:
            return f"❌ Mobile OCR failed: {str(e)}"

    @staticmethod
    def _mobile_apps(ai_engine: AIEngine = None) -> str:
        if not ai_engine:
            return "❌ AI engine required"
        try:
            mobile_eng = CommandExecutor._get_mobile_engine(ai_engine)
            if not mobile_eng.device:
                mobile_eng.connect()
            apps = mobile_eng.list_apps()
            return f"📱 Apps ({len(apps)}): {', '.join(apps[:20])}{'...' if len(apps)>20 else ''}"
        except Exception as e:
            return f"❌ Mobile apps list failed: {str(e)}"

    @staticmethod
    def _schedule_task(obj: dict, user_input: str, ai_engine: AIEngine) -> str:
        scheduler = CommandExecutor._get_scheduler()
        scheduler.start(lambda command_text: CommandExecutor._execute_scheduled_command(command_text, ai_engine))
        when_text = obj.get("when", "")
        repeat = obj.get("repeat", "once")
        command = obj.get("instruction") or obj.get("text") or user_input
        name = obj.get("name") or command[:40]

        when = CommandExecutor._parse_schedule_time(when_text, repeat)
        if when is None:
            return "❌ Could not understand schedule time. Use 'YYYY-MM-DD HH:MM' or phrases like 'daily'."
        return scheduler.schedule_task(name, command, when, repeat)

    @staticmethod
    def _list_scheduled_tasks() -> str:
        return CommandExecutor._get_scheduler().list_tasks()

    @staticmethod
    def _cancel_scheduled_task(name: str) -> str:
        if not name:
            return "❌ No scheduled task name provided"
        return CommandExecutor._get_scheduler().cancel_task(name)

    @staticmethod
    def _execute_scheduled_command(command_text: str, ai_engine: AIEngine = None):
        logger.info(f"Scheduled task triggered: {command_text}")
        if not ai_engine:
            return
        cmd_json = ai_engine.interpret_command(
            command_text,
            conversation_context=ai_engine.conversation_history,
            learning_engine=ai_engine.learning_engine,
        )
        try:
            CommandExecutor.execute(cmd_json, ai_engine, command_text)
        except Exception as exc:
            logger.error(f"Scheduled command execution failed: {exc}")

    @staticmethod
    def _parse_schedule_time(when_text: str, repeat: str):
        if when_text:
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%H:%M"):
                try:
                    parsed = datetime.strptime(when_text, fmt)
                    if fmt == "%H:%M":
                        now = datetime.now()
                        parsed = parsed.replace(year=now.year, month=now.month, day=now.day)
                        if parsed <= now:
                            parsed = parsed + timedelta(days=1)
                    return parsed
                except ValueError:
                    continue
        now = datetime.now()
        if repeat == "daily":
            scheduled = now.replace(hour=8, minute=0, second=0, microsecond=0)
            if scheduled <= now:
                scheduled += timedelta(days=1)
            return scheduled
        if repeat == "weekly":
            return now + timedelta(days=7)
        if repeat == "monthly":
            return now + timedelta(days=30)
        return None

    @staticmethod
    def _analyze_project(obj: dict, user_input: str) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        base_path = str(Path(obj.get("path", ".")).expanduser().resolve())
        request = obj.get("query") or user_input
        return assistant.analyze_project(base_path, request)

    @staticmethod
    def _search_code(obj: dict) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        return assistant.search_code(obj.get("query", obj.get("text", "")), obj.get("path", "."))

    @staticmethod
    def _find_symbol(obj: dict) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        return assistant.find_symbol(obj.get("name", obj.get("query", obj.get("text", ""))), obj.get("path", "."))

    @staticmethod
    def _list_todos(obj: dict) -> str:
        return CommandExecutor._get_developer_assistant().list_todos(obj.get("path", "."))

    @staticmethod
    def _find_dead_code(obj: dict) -> str:
        return CommandExecutor._get_developer_assistant().find_dead_code_candidates(obj.get("path", "."))

    @staticmethod
    def _generate_snippet(obj: dict) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        return assistant.generate_snippet(
            obj.get("snippet_type", obj.get("name", "")).lower(),
            obj.get("text", obj.get("query", "Example")),
            obj.get("framework", ""),
        )

    @staticmethod
    def _remember_developer_note(obj: dict, user_input: str) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        note = obj.get("text") or user_input
        category = obj.get("category") or "project_conventions"
        return assistant.memory.remember(category, note)

    @staticmethod
    def _recall_developer_memory(obj: dict) -> str:
        assistant = CommandExecutor._get_developer_assistant()
        return assistant.memory.recall(obj.get("category"))
    
    @staticmethod
    def _make_call(contact: str, ai_engine) -> str:
        """Trigger outgoing call popup via the GUI."""
        if not contact:
            return "❌ Who do you want to call? Say 'call mom' or 'call 9876543210'"
        # Try to reach the GUI window to show the popup
        try:
            from gi.repository import GLib
            # Walk all GTK windows to find BeautifulBenXGTK4
            import gi
            gi.require_version('Gtk', '4.0')
            from gi.repository import Gtk
            app = Gtk.Application.get_default()
            if app:
                for win in app.get_windows():
                    if hasattr(win, 'make_call'):
                        GLib.idle_add(win.make_call, contact)
                        return f"📞 Opening call dialog for '{contact}'…"
        except Exception as e:
            logger.warning("Could not reach GUI for call: %s", e)
        # Fallback: dial directly without popup
        from jarvis_ai.call_handler import lookup_contact, dial
        display_name, number = lookup_contact(contact)
        if number == contact and not contact.replace('+','').replace(' ','').isdigit():
            return f"❌ Could not find number for '{contact}'. Try saying the number directly."
        success, result = dial(number)
        return f"📞 Calling {display_name}…" if success else f"❌ Call failed: {result}"

    @staticmethod
    def _hangup_call() -> str:
        from jarvis_ai.call_handler import hangup_all
        return "📵 Call ended." if hangup_all() else "❌ No active call to hang up."

    @staticmethod
    def _handle_project_task(ai_engine: AIEngine, user_input: str, base_path: str) -> str:
        """Handle project orchestration tasks"""
        if not ai_engine:
            return "❌ AI engine required for project tasks"
        
        if not hasattr(ai_engine, 'project_orchestrator'):
            ai_engine.project_orchestrator = ProjectOrchestrator(ai_engine)
        
        return ai_engine.project_orchestrator.handle_project_request(user_input, base_path)

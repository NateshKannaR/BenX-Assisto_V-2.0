"""
Hyprland Dynamic Window Rules - Programmatic management of hyprland_rules.conf with hot-reloading.
"""
import logging
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

RULES_CONF_PATH = Path(__file__).resolve().parent.parent.parent / "hyprland_rules.conf"


class RulesManager:
    """Reads, updates, and hot-reloads Hyprland window rules."""

    @staticmethod
    def get_rules_path() -> Path:
        return RULES_CONF_PATH

    @staticmethod
    def reload_hyprland() -> bool:
        """Executes hyprctl reload to hot-apply configuration changes."""
        try:
            r = subprocess.run(["hyprctl", "reload"], capture_output=True, text=True, timeout=3)
            return r.returncode == 0
        except Exception as e:
            logger.warning(f"hyprctl reload failed: {e}")
            return False

    @staticmethod
    def list_rules() -> List[str]:
        """Returns list of active rules from hyprland_rules.conf."""
        p = RulesManager.get_rules_path()
        if not p.exists():
            return []
        try:
            with open(p, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            return lines
        except Exception as e:
            logger.error(f"Error reading {p}: {e}")
            return []

    @staticmethod
    def add_window_rule(rule_effect: str, match_target: str, match_type: str = "title") -> str:
        """
        Appends a new window rule to hyprland_rules.conf and triggers hyprctl reload.
        e.g. add_window_rule("float on", "mpv", "class")
             add_window_rule("size 800 600", "Calculator", "title")
        """
        p = RulesManager.get_rules_path()

        # Build rule statement: windowrule = <effect>, match:<match_type> ^(<target>)$
        rule_str = f"windowrule = {rule_effect}, match:{match_type} ^({match_target})$"

        try:
            existing = RulesManager.list_rules()
            if rule_str in existing:
                return f"⚠️ Rule already exists: {rule_str}"

            with open(p, "a", encoding="utf-8") as f:
                f.write(f"\n{rule_str}\n")

            reloaded = RulesManager.reload_hyprland()
            reload_msg = " (Hyprland configuration hot-reloaded)" if reloaded else " (reload pending)"
            return f"✅ Added window rule: '{rule_str}'{reload_msg}."
        except Exception as e:
            return f"❌ Failed to append window rule: {e}"

    @staticmethod
    def remove_window_rule(match_keyword: str) -> str:
        """Removes all window rules matching a keyword and reloads."""
        p = RulesManager.get_rules_path()
        if not p.exists():
            return "❌ hyprland_rules.conf not found."

        try:
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = [l for l in lines if match_keyword.lower() not in l.lower()]
            removed_count = len(lines) - len(new_lines)

            if removed_count == 0:
                return f"⚠️ No rules matching '{match_keyword}' found to remove."

            with open(p, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            RulesManager.reload_hyprland()
            return f"✅ Removed {removed_count} rule(s) matching '{match_keyword}' and reloaded Hyprland."
        except Exception as e:
            return f"❌ Failed to remove rule: {e}"

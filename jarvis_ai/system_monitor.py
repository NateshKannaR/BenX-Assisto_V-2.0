"""
BenX System Monitor - Background thread that proactively monitors system health
and sends alerts + AI-powered suggestions when thresholds are exceeded.
"""
import logging
import threading
import time
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    Background monitoring thread for CPU, RAM, battery, and temperature.
    Calls alert_callback when thresholds are exceeded with an AI-generated
    suggestion message. De-duplicates alerts with a cooldown period.
    """

    CHECK_INTERVAL = 30      # seconds between checks
    ALERT_COOLDOWN = 300     # seconds before re-alerting on same issue

    def __init__(self, ai_engine=None, alert_callback: Optional[Callable] = None):
        """
        Args:
            ai_engine:       BenX AIEngine instance (used to generate smart suggestions)
            alert_callback:  fn(title, message) called on threshold breach.
                             Falls back to desktop notification via notify-send.
        """
        self.ai_engine = ai_engine
        self.alert_callback = alert_callback or self._default_notify
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_alerts: dict[str, float] = {}

        try:
            from jarvis_ai.config import Config
            self._cfg = Config
        except Exception:
            self._cfg = None

    # ── Public API ──────────────────────────────────────────────
    def start(self):
        """Start the background monitor thread (daemon, non-blocking)."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="benx-system-monitor")
        self._thread.start()
        logger.info("✅ SystemMonitor started")

    def stop(self):
        """Signal the monitor to stop."""
        self._stop_event.set()
        logger.info("SystemMonitor stopped")

    # ── Internal ────────────────────────────────────────────────
    def _run(self):
        while not self._stop_event.is_set():
            try:
                self._check()
            except Exception as e:
                logger.debug(f"SystemMonitor check error: {e}")
            self._stop_event.wait(self.CHECK_INTERVAL)

    def _get_thresholds(self):
        if self._cfg:
            return {
                "cpu":     getattr(self._cfg, "MONITOR_CPU_THRESHOLD",     90),
                "ram":     getattr(self._cfg, "MONITOR_RAM_THRESHOLD",     88),
                "battery": getattr(self._cfg, "MONITOR_BATTERY_THRESHOLD", 15),
                "temp":    getattr(self._cfg, "MONITOR_TEMP_THRESHOLD",    85),
            }
        return {"cpu": 90, "ram": 88, "battery": 15, "temp": 85}

    def _check(self):
        try:
            import psutil
        except ImportError:
            return

        thresholds = self._get_thresholds()

        # CPU
        cpu = psutil.cpu_percent(interval=1)
        if cpu >= thresholds["cpu"]:
            self._maybe_alert("high_cpu", f"🔥 CPU at {cpu:.0f}%",
                              f"CPU usage is critically high ({cpu:.0f}%). "
                              f"Consider closing heavy processes or running `top` to diagnose.")

        # RAM
        mem = psutil.virtual_memory()
        if mem.percent >= thresholds["ram"]:
            self._maybe_alert("high_ram", f"💾 RAM at {mem.percent:.0f}%",
                              f"Memory usage is at {mem.percent:.0f}% "
                              f"({mem.used/1e9:.1f}GB / {mem.total/1e9:.1f}GB). "
                              f"Consider closing unused applications.")

        # Battery
        battery = psutil.sensors_battery()
        if battery and not battery.power_plugged and battery.percent <= thresholds["battery"]:
            self._maybe_alert("low_battery", f"🔋 Battery at {battery.percent:.0f}%",
                              f"Battery is critically low ({battery.percent:.0f}%). "
                              f"Plug in your charger soon. Want me to lower brightness to save power?")

        # Temperature
        try:
            temps = psutil.sensors_temperatures()
            max_temp = 0
            for sensor_list in temps.values():
                for s in sensor_list:
                    if s.current > max_temp:
                        max_temp = s.current
            if max_temp >= thresholds["temp"]:
                self._maybe_alert("high_temp", f"🌡️ CPU at {max_temp:.0f}°C",
                                  f"System temperature is high ({max_temp:.0f}°C). "
                                  f"Make sure cooling vents are clear and consider reducing workload.")
        except Exception:
            pass

    def _maybe_alert(self, key: str, title: str, message: str):
        """Fire alert only if cooldown has passed."""
        now = time.time()
        last = self._last_alerts.get(key, 0)
        if now - last < self.ALERT_COOLDOWN:
            return
        self._last_alerts[key] = now

        # Optionally enrich with AI suggestion
        if self.ai_engine:
            try:
                enriched = self.ai_engine.query_groq(
                    "You are BenX's proactive system advisor. Respond in 1-2 sentences max.",
                    f"System alert: {title} — {message}. Give one specific actionable tip.",
                    task_type="fast"
                )
                if enriched and "❌" not in enriched:
                    message = enriched
            except Exception:
                pass

        logger.warning(f"🚨 System Alert: {title} — {message}")
        try:
            self.alert_callback(title, message)
        except Exception as e:
            logger.debug(f"Alert callback error: {e}")

    @staticmethod
    def _default_notify(title: str, message: str):
        """Send a desktop notification via notify-send (Linux)."""
        import subprocess, shutil
        if shutil.which("notify-send"):
            subprocess.Popen(
                ["notify-send", "-u", "critical", "-t", "8000", f"BenX: {title}", message],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        else:
            print(f"\n⚠️  [{title}] {message}\n")


# ── Module-level singleton ────────────────────────────────────
_monitor: Optional[SystemMonitor] = None


def get_monitor(ai_engine=None, alert_callback=None) -> SystemMonitor:
    """Get or create the global SystemMonitor singleton."""
    global _monitor
    if _monitor is None:
        _monitor = SystemMonitor(ai_engine=ai_engine, alert_callback=alert_callback)
    return _monitor


def start_monitor(ai_engine=None, alert_callback=None):
    """Convenience: create and start the monitor."""
    try:
        from jarvis_ai.config import Config
        if not getattr(Config, "SYSTEM_MONITOR_ENABLED", True):
            logger.info("SystemMonitor disabled by config")
            return None
    except Exception:
        pass
    m = get_monitor(ai_engine, alert_callback)
    m.start()
    return m

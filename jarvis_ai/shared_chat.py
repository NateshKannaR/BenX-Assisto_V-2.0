"""
Shared chat store — thread-safe JSON file that both GTK4 and Web UI read/write.
"""
import json
import threading
from datetime import datetime, timezone
from jarvis_ai.config import Config

_lock = threading.Lock()
_MAX = 200  # keep last N messages


def _load() -> list:
    try:
        if Config.SHARED_CHAT_FILE.exists():
            return json.loads(Config.SHARED_CHAT_FILE.read_text())
    except Exception:
        pass
    return []


def _save(messages: list):
    Config.SHARED_CHAT_FILE.write_text(json.dumps(messages[-_MAX:], indent=2))


def append(sender: str, text: str, source: str = "gtk4") -> dict:
    """Add a message. source = 'gtk4' | 'web'"""
    msg = {
        "id": datetime.now(tz=timezone.utc).timestamp(),
        "sender": sender,
        "text": text,
        "source": source,
        "timestamp": datetime.now(tz=timezone.utc).astimezone().strftime("%H:%M:%S"),
    }
    with _lock:
        msgs = _load()
        msgs.append(msg)
        _save(msgs)
    return msg


def get_since(since_id: float = 0.0) -> list:
    """Return messages newer than since_id (timestamp float)."""
    with _lock:
        return [m for m in _load() if m.get("id", 0) > since_id]


def get_all(limit: int = 100) -> list:
    with _lock:
        return _load()[-limit:]

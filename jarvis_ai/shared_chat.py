"""
Shared chat store — MongoDB backed so GTK4 and Vercel web instances share the same messages.
Falls back to in-memory list if MongoDB is unavailable.
"""
import threading
from datetime import datetime, timezone
from jarvis_ai.config import Config

_lock = threading.Lock()
_fallback: list = []  # used only if MongoDB is down

def _col():
    """Return MongoDB collection, or None if unavailable."""
    if not Config.MONGODB_URI:
        return None
    try:
        from pymongo import MongoClient
        client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=3000)
        return client["benx"]["shared_chat"]
    except Exception:
        return None


def append(sender: str, text: str, source: str = "gtk4") -> dict:
    """Add a message. source = 'gtk4' | 'web'"""
    msg = {
        "id": datetime.now(tz=timezone.utc).timestamp(),
        "sender": sender,
        "text": text,
        "source": source,
        "timestamp": datetime.now(tz=timezone.utc).astimezone().strftime("%H:%M:%S"),
    }
    col = _col()
    if col is not None:
        col.insert_one({**msg})
        # Keep only last 200 messages
        count = col.count_documents({})
        if count > 200:
            oldest = col.find({}, {"_id": 1}).sort("id", 1).limit(count - 200)
            col.delete_many({"_id": {"$in": [d["_id"] for d in oldest]}})
    else:
        with _lock:
            _fallback.append(msg)
            if len(_fallback) > 200:
                _fallback.pop(0)
    return msg


def get_since(since_id: float = 0.0) -> list:
    """Return messages newer than since_id (epoch float)."""
    col = _col()
    if col is not None:
        return [
            {k: v for k, v in m.items() if k != "_id"}
            for m in col.find({"id": {"$gt": since_id}}).sort("id", 1)
        ]
    with _lock:
        return [m for m in _fallback if m.get("id", 0) > since_id]


def get_all(limit: int = 100) -> list:
    col = _col()
    if col is not None:
        return [
            {k: v for k, v in m.items() if k != "_id"}
            for m in col.find({}).sort("id", -1).limit(limit)
        ]
    with _lock:
        return _fallback[-limit:]

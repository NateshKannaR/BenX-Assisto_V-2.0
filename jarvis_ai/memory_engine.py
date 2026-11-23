"""
BenX Memory Engine - Persistent user facts + smart recall
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import defaultdict

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

logger = logging.getLogger(__name__)

from jarvis_ai.config import Config

class MemoryEngine:
    def __init__(self, memory_file: Path = None):
        self.memory_file = memory_file or Path.home() / ".benx" / "memory.json"
        self.facts_file = self.memory_file.parent / "user_facts.json"
        
        # MongoDB client for cross-platform sync
        self.mongo_client = None
        self.db = None
        if MONGO_AVAILABLE and Config.MONGODB_URI:
            try:
                self.mongo_client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=3000)
                self.db = self.mongo_client[Config.DATABASE_NAME]
                self.mongo_client.admin.command("ping")  # Test connection
                logger.info("✅ MongoDB Atlas connected")
            except Exception as e:
                if self.mongo_client is not None:
                    self.mongo_client.close()
                self.mongo_client = None
                self.db = None
                logger.warning("MongoDB connection failed (%s); using local memory", type(e).__name__)
        
        self.short_term = []
        self.long_term = defaultdict(list)
        self.facts = {}
        self.load_memory()

    def load_memory(self):
        # Try MongoDB first (cross-platform)
        if self.db is not None:  # explicit None check — pymongo Database has no bool
            try:
                facts_cursor = self.db.facts.find()
                self.facts = {doc["key"]: doc["value"] for doc in facts_cursor}
                
                short_cursor = self.db.short_term.find().sort("timestamp", -1).limit(100)
                self.short_term = list(short_cursor)
                
                # Load long_term categories
                for cat in ["general", "session_summaries"]:
                    cat_cursor = self.db.long_term.find({"category": cat}).sort("timestamp", -1)
                    self.long_term[cat] = list(cat_cursor)
                logger.info("✅ Loaded memory from MongoDB")
                return
            except Exception as e:
                logger.warning(f"MongoDB load failed: {e}")
        
        # Fallback to local JSON
        try:
            if self.memory_file.exists():
                data = json.loads(self.memory_file.read_text())
                self.short_term = data.get("short_term", [])[-100:]
                self.long_term = defaultdict(list, data.get("long_term", {}))
        except Exception as e:
            logger.error(f"Local memory load failed: {e}")
        try:
            if self.facts_file.exists():
                self.facts = json.loads(self.facts_file.read_text())
        except Exception:
            self.facts = {}

    def save_memory(self):
        # Sync to MongoDB first
        if self.db is not None:  # explicit None check
            try:
                # Save facts
                for key, value in self.facts.items():
                    self.db.facts.update_one(
                        {"key": key}, 
                        {"$set": {"key": key, "value": value, "updated_at": datetime.now().isoformat()}}, 
                        upsert=True
                    )
                
                # Save short_term
                for entry in self.short_term[-10:]:  # Recent only
                    entry["updated_at"] = datetime.now().isoformat()
                    self.db.short_term.update_one(
                        {"_id": entry.get("_id")}, 
                        {"$set": entry}, 
                        upsert=True
                    )
                
                logger.debug("✅ Synced memory to MongoDB")
            except Exception as e:
                logger.warning(f"MongoDB save failed: {e}")
        
        # Local backup
        try:
            self.memory_file.write_text(json.dumps({
                "short_term": self.short_term[-100:],
                "long_term": dict(self.long_term),
            }, indent=2))
        except Exception as e:
            logger.error(f"Local memory save failed: {e}")

    def save_facts(self):
        self.save_memory()  # Now handles both

    def get_browser_state(self, ws_id: Optional[int] = None) -> dict:
        """Get browser state for workspace (tabs, etc.)."""
        state = self.get_fact('browser_state') or '{}'
        try:
            data = json.loads(state)
            return data.get(str(ws_id), {})
        except:
            return {}

    def save_browser_state(self, ws_id: int, state: dict):
        """Save browser state for workspace."""
        all_state = self.get_fact('browser_state') or '{}'
        try:
            data = json.loads(all_state)
        except:
            data = {}
        data[str(ws_id)] = state
        self.learn_fact('browser_state', json.dumps(data))

    def remember(self, user_input: str, response: str, category: str = "general", device_id: str = "local"):
        entry = {
            "_id": f"{device_id}_{datetime.now().isoformat()}",
            "timestamp": datetime.now().isoformat(),
            "device_id": device_id,
            "user": user_input,
            "assistant": response,
            "category": category
        }
        self.short_term.append(entry)
        self.long_term[category].append(entry)
        # Auto-extract facts from conversation
        self._auto_extract_facts(user_input)
        self.save_memory()

    def _auto_extract_facts(self, text: str):
        """Auto-detect user facts from natural language."""
        import re
        patterns = [
            (r"my name is (\w+)", "user_name"),
            (r"i(?:'m| am) (\w+)", "user_name"),
            (r"call me (\w+)", "user_name"),
            (r"i(?:'m| am) a[n]? ([\w\s]+)", "user_role"),
            (r"i work (?:at|for|in) ([\w\s]+)", "workplace"),
            (r"i(?:'m| am) (?:from|in|at) ([\w\s]+)", "location"),
            (r"i prefer ([\w\s]+)", "preference"),
            (r"i use ([\w\s]+) for", "tool_preference"),
            (r"my (?:email|mail) is ([\w@.]+)", "email"),
            (r"my project is ([\w\s/~.]+)", "current_project"),
        ]
        t = text.lower()
        for pattern, key in patterns:
            m = re.search(pattern, t)
            if m:
                val = m.group(1).strip()
                if len(val) > 1 and val not in ("a", "an", "the"):
                    self.facts[key] = val
                    self.save_facts()

    def learn_fact(self, key: str, value: str):
        self.facts[key.lower().strip()] = value
        self.save_facts()

    def get_fact(self, key: str) -> Optional[str]:
        return self.facts.get(key.lower().strip())

    def recall(self, query: str, limit: int = 5):
        q = query.lower()
        return [
            m for m in reversed(self.short_term)
            if q in m.get("user", "").lower() or q in m.get("assistant", "").lower()
        ][:limit]

    def get_user_facts_summary(self) -> str:
        if not self.facts:
            return ""
        lines = ["Known about user:"]
        for k, v in self.facts.items():
            lines.append(f"  - {k.replace('_', ' ')}: {v}")
        return "\n".join(lines)

    def get_context_summary(self) -> str:
        if not self.short_term:
            return ""
        recent = self.short_term[-3:]
        lines = ["Recent context:"]
        for m in recent:
            lines.append(f"  - {m['user'][:60]}")
        return "\n".join(lines)

    def generate_session_summary(self, ai_engine=None) -> str:
        """Generate a brief summary of this session and store it in long-term memory.
        Called at session end or periodically to capture key events.
        """
        if len(self.short_term) < 3:
            return ""
        recent = self.short_term[-20:]
        convo = "\n".join(
            f"User: {m['user'][:100]}\nBenX: {m['assistant'][:100]}"
            for m in recent
        )
        summary = f"Session summary ({datetime.now().strftime('%Y-%m-%d %H:%M')}): {len(recent)} interactions."
        if ai_engine:
            try:
                summary = ai_engine.query_groq(
                    "You are BenX's memory summarizer. Summarize in 2-3 sentences max.",
                    f"Summarize this session:\n{convo[:1500]}",
                    task_type="fast"
                )
            except Exception:
                pass
        self.long_term["session_summaries"].append({
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "message_count": len(recent)
        })
        # Keep only last 20 summaries
        self.long_term["session_summaries"] = self.long_term["session_summaries"][-20:]
        self.save_memory()
        return summary

    def get_predictive_suggestions(self, limit: int = 3) -> list:
        """Return the most frequently asked user patterns for proactive suggestions."""
        from collections import Counter
        if len(self.short_term) < 5:
            return []
        # Count common keywords in recent user messages
        words = []
        for m in self.short_term[-50:]:
            words.extend(m.get("user", "").lower().split())
        stop = {"i", "a", "the", "to", "my", "me", "can", "you", "please", "what", "how", "is", "in", "and", "or", "for"}
        counter = Counter(w for w in words if w not in stop and len(w) > 3)
        top = [word for word, _ in counter.most_common(limit)]
        return top

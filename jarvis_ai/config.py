"""
Configuration settings for BenX
"""
import os
from pathlib import Path
from typing import List

class Config:
    """Configuration class for BenX"""
    
    # MongoDB Atlas for cross-platform sync (GTK4/Web/Mobile)
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://Natesh:Natesh@cluster0.wwp3oig.mongodb.net/?retryWrites=true&w=majority")
    DATABASE_NAME = "benx"
    
# API Configuration (Multi-provider)
    # Set environment variables:
    # export GROQ_API_KEY='...'
    # export OPENAI_API_KEY='...'
    # export OLLAMA_URL='http://localhost:11434'
    GROQ_KEY = os.getenv("GROQ_API_KEY", os.getenv("GROQ_KEY", "")).strip()
    OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip()
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    
    # ── Model routing: task-type → best model ──────────────────────
    MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "groq/compound",
        "groq/compound-mini",
        "qwen/qwen3-32b",
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "moonshotai/kimi-k2-instruct",
    ]

    # Ordered fallback lists per task type
    MODEL_ROUTES = {
        "vision":  ["meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.3-70b-versatile", "groq/compound"],
        "code":    ["qwen/qwen3-32b", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"],
        "chat":    ["llama-3.3-70b-versatile", "groq/compound", "llama-3.1-8b-instant"],
        "fast":    ["llama-3.1-8b-instant", "groq/compound-mini", "llama-3.3-70b-versatile"],
        "reason":  ["openai/gpt-oss-120b", "moonshotai/kimi-k2-instruct", "llama-3.3-70b-versatile"],
    }

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    API_TIMEOUT = 120

    # Email (IMAP/SMTP)
    EMAIL_ADDRESS  = os.getenv("BENX_EMAIL", "").strip()
    EMAIL_PASSWORD = os.getenv("BENX_EMAIL_PASSWORD", "").strip()
    EMAIL_IMAP     = os.getenv("BENX_IMAP", "imap.gmail.com").strip()
    EMAIL_SMTP     = os.getenv("BENX_SMTP", "smtp.gmail.com").strip()
    EMAIL_SMTP_PORT = int(os.getenv("BENX_SMTP_PORT", "587"))

    HOME = Path.home()

    # Use /tmp on serverless (Vercel), ~/.benx on desktop
    _base = Path("/tmp/benx") if not (Path.home() / ".benx").parent.exists() or os.getenv("VERCEL") else Path.home() / ".benx"
    BENX_DIR = _base
    try:
        BENX_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        BENX_DIR = Path("/tmp/benx")
        BENX_DIR.mkdir(parents=True, exist_ok=True)

    ACTIVITY_LOG_FILE = BENX_DIR / "activity_log.json"
    SUDO_ALLOWED_PATHS = ["/home", "/tmp", "/var/tmp"]  # Expandable
    SHELL_RATE_LIMIT = 5  # Commands per minute
    REQUIRE_SUDO_CONFIRM = True  # Prompt for sudo
    
    # Safety/permissions
    REQUIRE_CONFIRMATION = True
    PROMPT_FOR_SUDO = True
    ALLOWED_ROOTS = [
        str(Path.home()),
        "/tmp",
        "/var/tmp"
    ]
    
    # RAG Configuration
    RAG_ENABLED = True
    RAG_EMBEDDINGS_MODEL = "text-embedding-3-small"  # For text embeddings
    VECTOR_DB_PATH = None  # Will be set in __init__
    MAX_CONTEXT_LENGTH = 128000  # Maximum context window
    EMBEDDING_CACHE_SIZE = 512   # Max entries in LRU embedding cache

    # AI Engine Features
    MULTI_MODEL_VOTING_ENABLED = True   # Vote between top-2 models for reasoning tasks
    ASYNC_ENABLED = True                # Use async paths in FastAPI server

    # System Monitor
    SYSTEM_MONITOR_ENABLED = True
    MONITOR_CPU_THRESHOLD    = 90   # % CPU to alert at
    MONITOR_BATTERY_THRESHOLD = 15  # % battery to warn at
    MONITOR_RAM_THRESHOLD    = 88   # % RAM to alert at
    MONITOR_TEMP_THRESHOLD   = 85   # °C to alert at
    
    # Image processing - vision models (may not be available)
    IMAGE_MODELS = [
        "meta-llama/llama-4-scout-17b-16e-instruct",  # Llama 4 Scout - vision capable
        "llama-3.3-70b-versatile",  # Fallback to best text model
        "groq/compound",  # Compound model
    ]
    MAX_IMAGE_SIZE = 2048  # Max image dimension for processing
    IMAGE_CACHE_DIR = None  # Will be set in __init__
    
    # Paths
    LOG_FILE = BENX_DIR / "benx.log"
    HISTORY_FILE = BENX_DIR / "history.txt"
    CONVERSATION_FILE = BENX_DIR / "conversation.json"
    SCREENSHOT_PATH = "/tmp/benx_screen.png"
    SCREEN_ANALYSIS_PATH = BENX_DIR / "screen_analysis.json"
    LEARNING_FILE = BENX_DIR / "learning.json"
    DEVELOPER_MEMORY_FILE = BENX_DIR / "developer_memory.json"
    SCHEDULE_FILE = BENX_DIR / "scheduled_tasks.json"
    SHARED_CHAT_FILE = BENX_DIR / "shared_chat.json"
    AUTOMATION_STATE_FILE = BENX_DIR / "automation_state.json"
    RAG_DATA_DIR = BENX_DIR / "rag_data"

    # Create directories safely
    try:
        RAG_DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    VECTOR_DB_PATH = RAG_DATA_DIR / "vector_db.pkl"
    IMAGE_CACHE_DIR = RAG_DATA_DIR / "images"
    try:
        IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    
    # System tools with fallbacks
    TOOLS = {
        "screenshot": ["grim", "maim", "scrot", "gnome-screenshot"],
        "volume": ["pamixer", "amixer", "pactl"],
        "brightness": ["brightnessctl", "xbacklight", "light"],
        "network": ["nmcli", "iwconfig"],
        "media": ["playerctl", "mpc"],
        "file_manager": ["xdg-open", "nautilus", "thunar", "dolphin"],
        "window_manager": ["hyprctl", "wmctrl", "xdotool"]
    }
    
    # Limits
    MAX_VOLUME = 100
    MIN_VOLUME = 0
    MAX_BRIGHTNESS = 100
    MIN_BRIGHTNESS = 0
    
    # GUI Settings (Advanced control center)
    WINDOW_WIDTH = 1400
    WINDOW_HEIGHT = 820
    WINDOW_OPACITY = 0.97  # Semi-transparent floating effect
    FONT_FAMILY = "Rajdhani"
    HEADING_FONT_FAMILY = "Orbitron"
    THEME_COLOR = "#0b1720"  # Deep panel
    ACCENT_COLOR = "#20d9ff"  # Neon cyan
    ACCENT_COLOR_2 = "#2be2a4"  # Neon green
    TEXT_COLOR = "#d3f0ff"  # Light text
    BG_COLOR = "#060c10"  # App background
    SECONDARY_COLOR = "#0c222c"  # Secondary background
    GLASS_COLOR = "#0c1f27"  # Glass panel
    GLASS_COLOR_DARK = "#08161c"  # Glass panel deep
    GLASS_BORDER = "#173640"  # Glass border
    GLASS_HIGHLIGHT = "#1fd9ff"  # Glass highlight
    SUCCESS_COLOR = "#34d399"  # Green
    ERROR_COLOR = "#f87171"  # Red
    WARNING_COLOR = "#fbbf24"  # Yellow



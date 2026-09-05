#!/bin/bash
set -e

cd "$(dirname "$0")"

# Activate venv
if [ -d "benx_venv" ]; then
    source benx_venv/bin/activate
else
    echo "❌ benx_venv not found. Run setup_and_run.sh first."
    exit 1
fi

echo "🔄 Testing MongoDB connection..."
python3 -c "
from jarvis_ai.memory_engine import MemoryEngine
me = MemoryEngine()
print('✅ MongoDB ready' if me.db is not None else '⚠️ Using local fallback')
"

echo "🌐 BenX Web Server (w/ Mobile Control + MongoDB) starting..."
echo "Web UI: http://localhost:8001"
echo "Mobile WS: ws://localhost:8000/ws"
echo "  Run both for full cross-platform sync!"

# Start web UI server (main.py)
cd src && python3 main.py --port 8001 &
WEB_PID=$!

# Start remote control server (port 8000 for mobile)
cd ../jarvis_ai && python3 remote_control.py &
REMOTE_PID=$!

# Wait for servers
wait $WEB_PID $REMOTE_PID


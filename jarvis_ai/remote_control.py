"""
BenX Remote Control Server - Bi-directional mobile/laptop control
FastAPI WebSocket + QR pairing + command relay
Run: uvicorn jarvis_ai.remote_control:app --port 8000 --host 0.0.0.0
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import json
import qrcode
from PIL import Image
from io import BytesIO
import base64
import subprocess
from typing import Dict, Any
from pathlib import Path
import secrets
from jarvis_ai.executor import CommandExecutor
from jarvis_ai.ai_engine import AIEngine
from jarvis_ai.command_engine import CommandEngine
from jarvis_ai.config import Config
from jarvis_ai.memory_engine import MemoryEngine

app = FastAPI(title="BenX Remote Control")

# Pairing tokens
clients: Dict[str, WebSocket] = {}
tokens: Dict[str, str] = {}  # token → device_name
ai_engine = AIEngine()
memory_engine = MemoryEngine()

@app.get("/")
async def root():
    return {"message": "BenX Remote Server running. Connect mobile WS to wss://IP:8000/ws"}

@app.get("/qr/{device}")
async def generate_qr(device: str):
    """Generate QR for pairing"""
    token = secrets.token_urlsafe(32)
    tokens[token] = device
    qr = qrcode.QRCode()
    qr.add_data(f"benx://pair/{token}")
    qr.make()
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return HTMLResponse(content=f'''
<!DOCTYPE html>
<html>
<body>
<h1>BenX Pairing QR - {device}</h1>
<img src="data:image/png;base64,{base64.b64encode(bio.read()).decode()}">
<p>Scan on mobile Stitch app</p>
</body>
</html>
    ''', status_code=200)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    device = None
    token = None
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            cmd = msg.get("cmd")
            
            if cmd == "pair":
                token = msg.get("token")
                device_name = msg.get("device_name", "mobile")
                if token in tokens:
                    device = tokens.pop(token)
                    clients[device] = websocket
                    # Log session to MongoDB
                    memory_engine.remember(
                        f"Mobile device '{device}' paired", 
                        f"Remote control session started for {device}",
                        category="remote_sessions",
                        device_id=device
                    )
                    await websocket.send_text(json.dumps({"status": "paired", "device": device}))
                    print(f"✅ Paired: {device}")
                else:
                    await websocket.send_text(json.dumps({"error": "invalid token"}))
            elif cmd == "type":
                text = msg.get("text", "")
                result = CommandEngine.type_in_active_window(text)
                memory_engine.remember(f"Remote type: {text[:50]}", result, "remote_commands", device)
                await websocket.send_text(json.dumps({"result": result}))
            elif cmd == "click":
                x, y = msg.get("x", 0), msg.get("y", 0)
                import pyautogui
                pyautogui.click(x, y)
                await websocket.send_text(json.dumps({"result": f"Clicked ({x},{y})"}))
            elif cmd == "screenshot":
                result = CommandEngine.take_screenshot()
                # Send base64 image
                with open(Config.SCREENSHOT_PATH, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                await websocket.send_text(json.dumps({"result": result, "screenshot": img_b64}))
            elif cmd == "voice":
                text = msg.get("text")
                # TTS on laptop
                import pyttsx3
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
                await websocket.send_text(json.dumps({"result": "Spoke: " + text}))
            elif cmd == "cmd":
                cmd_str = msg.get("command")
                result = CommandEngine.shell_execute(cmd_str)
                memory_engine.remember(f"Remote shell: {cmd_str[:50]}", result, "remote_commands", device)
                await websocket.send_text(json.dumps({"result": result}))
            else:
                await websocket.send_text(json.dumps({"error": "unknown cmd"}))
    except WebSocketDisconnect:
        if device:
            clients.pop(device, None)
            memory_engine.remember(f"Device {device} disconnected", "Remote session ended", "remote_sessions", device)
            print(f"❌ Disconnected: {device}")

@app.get("/mobile/{token}")
async def mobile_page(token: str):
    """Mobile control page (for Stitch WebView fallback)"""
    if token in tokens:
        device = tokens[token]
        return HTMLResponse(content=f'''
<!DOCTYPE html>
<html>
<head>
<title>BenX {device}</title>
<script>
const ws = new WebSocket(`ws://${location.host}/ws`);
ws.onopen = () => {{
    ws.send(JSON.stringify({{cmd: "pair", token: "{token}"}}));
}};
function sendType() {{
    ws.send(JSON.stringify({{cmd: "type", text: document.getElementById('text').value}}));
}}
</script>
</head>
<body>
<h1>BenX {device}</h1>
<input id="text" type="text" placeholder="Type...">
<button onclick="sendType()">Send to Laptop</button>
<div id="screenshot"></div>
</body>
</html>
        ''')
    return {"error": "invalid token"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


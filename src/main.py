#!/usr/bin/env python3
"""
BenX Web Server - FastAPI backend for the Web UI
Connects the browser frontend to the real BenX AI engine.
"""
import sys
import os
import json
import logging
import asyncio
import time
import secrets
from concurrent.futures import TimeoutError as ConfirmationTimeout
from contextlib import aclosing
from pathlib import Path
from typing import Optional, AsyncGenerator
from datetime import datetime

# Add parent dir to path so jarvis_ai is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
import psutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ── Lazy-load heavy AI components so server starts fast ──────────────────────
_ai_engine = None
_executor_cls = None

def get_ai_engine():
    global _ai_engine
    if _ai_engine is None:
        from jarvis_ai.ai_engine import AIEngine
        _ai_engine = AIEngine()
        logger.info("✅ AIEngine initialised")
    return _ai_engine

def get_memory_engine():
    global _memory_engine
    if '_memory_engine' not in globals():
        from jarvis_ai.memory_engine import MemoryEngine
        from jarvis_ai.config import Config
        _memory_engine = MemoryEngine()
        logger.info("✅ MemoryEngine with MongoDB initialised")
    return _memory_engine

def get_executor():
    global _executor_cls
    if _executor_cls is None:
        from jarvis_ai.executor import CommandExecutor
        _executor_cls = CommandExecutor
    return _executor_cls

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="BenX API", version="2.0.0")

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

@app.middleware("http")
async def require_local_browser(request: Request, call_next):
    origin = request.headers.get("origin")
    expected_origin = f"{request.url.scheme}://{request.headers.get('host', '')}"
    if (origin is not None and origin != expected_origin) or (
        request.headers.get("sec-fetch-site") in {"cross-site", "same-site"}
    ):
        return JSONResponse({"detail": "Open BenX directly in your browser."}, status_code=403)
    return await call_next(request)


_pending_confirmations: dict[str, asyncio.Future] = {}


class Confirmation(BaseModel):
    approved: bool


@app.post("/api/confirm/{request_id}", status_code=204)
async def confirm_command(request_id: str, decision: Confirmation):
    pending = _pending_confirmations.pop(request_id, None)
    if pending is None or pending.done():
        raise HTTPException(status_code=404, detail="Confirmation request expired")
    pending.set_result(decision.approved)


async def _execute_with_confirmation(executor, command, ai, user_input, interactive):
    loop = asyncio.get_running_loop()
    prompts = asyncio.Queue()
    request_ids = set()

    async def ask(prompt):
        request_id = secrets.token_urlsafe(24)
        decision = loop.create_future()
        request_ids.add(request_id)
        _pending_confirmations[request_id] = decision
        await prompts.put({"type": "confirmation", "id": request_id, "text": prompt})
        try:
            return await asyncio.wait_for(decision, timeout=60)
        except asyncio.TimeoutError:
            return False
        finally:
            request_ids.discard(request_id)
            _pending_confirmations.pop(request_id, None)

    active = True
    rejected = False

    def confirm(prompt):
        nonlocal rejected
        if not interactive or not active:
            rejected = True
            return False
        future = asyncio.run_coroutine_threadsafe(ask(prompt), loop)
        try:
            return future.result(timeout=65)
        except ConfirmationTimeout:
            future.cancel()
            return False

    task = loop.run_in_executor(None, executor.execute, command, ai, user_input, confirm)
    prompt_task = None
    try:
        while not task.done():
            prompt_task = asyncio.create_task(prompts.get())
            done, _ = await asyncio.wait({task, prompt_task}, return_when=asyncio.FIRST_COMPLETED)
            if prompt_task in done and task not in done:
                yield prompt_task.result()
        result = task.result()
        if rejected:
            result = "This action requires confirmation. Use the live BenX web UI or desktop app."
        yield {"type": "command_result", "action": json.loads(command)["command"], "text": result}
    finally:
        active = False
        if prompt_task is not None:
            prompt_task.cancel()
        for request_id in tuple(request_ids):
            pending = _pending_confirmations.pop(request_id, None)
            if pending is not None and not pending.done():
                pending.set_result(False)


# Serve static files
_src_dir = Path(__file__).parent
app.mount("/css", StaticFiles(directory=str(_src_dir / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(_src_dir / "js")), name="js")

# ── WebSocket connection manager ──────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    html_file = _src_dir / "index.html"
    return HTMLResponse(content=html_file.read_text(), status_code=200)


@app.get("/assets/benx.jpg")
async def benx_image():
    return FileResponse(_src_dir.parent / "benx.jpg")


@app.get("/api/messages")
async def get_messages(since: float = 0.0):
    """Return shared chat messages newer than since (epoch float)."""
    try:
        from jarvis_ai.shared_chat import get_since
        return {"messages": get_since(since)}
    except Exception as e:
        return {"messages": [], "error": str(e)}


@app.post("/api/messages")
async def post_message(data: dict):
    """Web UI posts a message to the shared store."""
    try:
        from jarvis_ai.shared_chat import append as shared_append
        msg = shared_append(data.get("sender", "You"), data.get("text", ""), source="web")
        return {"ok": True, "id": msg["id"]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}


@app.get("/api/metrics")
async def get_metrics():
    """Return real system metrics."""
    try:
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net_io = psutil.net_io_counters()
        battery = psutil.sensors_battery()

        # Network KB/s estimate (cumulative counters — use cached delta)
        net_kbps = getattr(get_metrics, "_net_kbps", 0)
        prev = getattr(get_metrics, "_prev_net", None)
        now_bytes = net_io.bytes_recv + net_io.bytes_sent
        now_ts = time.time()
        if prev:
            delta_bytes, delta_t = now_bytes - prev[0], now_ts - prev[1]
            if delta_t > 0:
                net_kbps = max(0, delta_bytes / delta_t / 1024)
        get_metrics._prev_net = (now_bytes, now_ts)
        get_metrics._net_kbps = net_kbps

        # CPU temp
        temp = 0
        try:
            temps = psutil.sensors_temperatures()
            for sensor_list in temps.values():
                for s in sensor_list:
                    if s.current > 0:
                        temp = s.current
                        break
                if temp:
                    break
        except Exception:
            pass

        return {
            "cpu": round(cpu, 1),
            "ram": round(mem.percent, 1),
            "ram_used_gb": round(mem.used / 1e9, 2),
            "ram_total_gb": round(mem.total / 1e9, 2),
            "disk": round(disk.percent, 1),
            "disk_used_gb": round(disk.used / 1e9, 1),
            "disk_total_gb": round(disk.total / 1e9, 1),
            "network_kbps": round(net_kbps, 1),
            "temp": round(temp, 1),
            "battery": round(battery.percent, 1) if battery else None,
            "charging": battery.power_plugged if battery else None,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return {"error": str(e)}


@app.get("/api/history")
async def get_history(limit: int = 30):
    """Return recent conversation messages."""
    try:
        ai = get_ai_engine()
        msgs = ai.conversation_history[-limit:]
        return {"messages": msgs, "count": len(msgs)}
    except Exception as e:
        return {"messages": [], "error": str(e)}


@app.post("/api/history/clear")
async def clear_history():
    """Clear conversation history from AI engine memory."""
    try:
        ai = get_ai_engine()
        ai.conversation_history = []
        ai.save_conversation_history()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/models")
async def get_models():
    """Return available model list from config."""
    try:
        from jarvis_ai.config import Config
        return {"models": Config.MODELS, "routes": Config.MODEL_ROUTES}
    except Exception as e:
        return {"models": [], "error": str(e)}

@app.get("/api/mobile/devices")
async def mobile_devices():
    """List connected mobile devices"""
    try:
        from jarvis_ai.mobile_automation import MobileAutomationEngine
        eng = MobileAutomationEngine()
        devices = [d.serial for d in eng.client.devices()]
        return {"devices": devices}
    except Exception as e:
        return {"devices": [], "error": str(e)}

@app.get("/api/mobile/apps")
async def mobile_apps():
    """List apps on connected device"""
    try:
        from jarvis_ai.mobile_automation import MobileAutomationEngine
        eng = MobileAutomationEngine()
        apps = eng.list_apps()
        return {"apps": apps[:100]}  # Limit
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/mobile/automate")
async def mobile_automate(instruction: str):
    """Run mobile automation"""
    try:
        from jarvis_ai.ai_engine import AIEngine
        from jarvis_ai.mobile_automation import MobileAutomationEngine
        ai = AIEngine()
        eng = MobileAutomationEngine(ai)
        result = eng.automate(instruction)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


async def _stream_chat_response(user_input: str, model: Optional[str], agent_mode: bool, *, interactive: bool = False) -> AsyncGenerator[str, None]:
    """Core streaming generator used by both SSE and WebSocket paths."""
    ai = get_ai_engine()
    executor = get_executor()

    yield json.dumps({"type": "status", "text": "🧠 Interpreting command..."}) + "\n"

    # First try command interpretation
    try:
        cmd_json = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: ai.interpret_command(
                user_input,
                conversation_context=ai.conversation_history,
                learning_engine=ai.learning_engine
            )
        )
        cmd_obj = json.loads(cmd_json)
        action = cmd_obj.get("command", "none")
    except Exception:
        action = "none"
        cmd_json = '{"command":"none"}'

    if action != "none":
        yield json.dumps({"type": "status", "text": f"⚡ Executing: {action}"}) + "\n"
        try:
            async with aclosing(
                _execute_with_confirmation(executor, cmd_json, ai, user_input, interactive)
            ) as events:
                async for event in events:
                    if event["text"] is not None:
                        yield json.dumps(event) + "\n"
                        if event["type"] == "command_result":
                            yield json.dumps({"type": "done"}) + "\n"
                            return
        except Exception as e:
            yield json.dumps({"type": "error", "text": f"Command error: {e}"}) + "\n"

    # Chat / conversational response via streaming
    yield json.dumps({"type": "status", "text": "💬 Thinking..."}) + "\n"

    system_state = await asyncio.get_event_loop().run_in_executor(None, ai._get_system_context)

    system_prompt = f"""You are BenX, an ultra-advanced AI personal assistant with complete control over the user's Linux system.
Be concise, direct, and helpful. Format responses with markdown when appropriate.

CURRENT SYSTEM STATE:
{system_state}"""

    ai.conversation_history.append({"role": "user", "content": user_input})

    # Stream the response token by token
    full_response = ""
    try:
        gen = ai.query_groq(
            system_prompt,
            user_input,
            conversation_context=ai.conversation_history,
            stream=True
        )
        for chunk in gen:
            if chunk:
                full_response += chunk
                yield json.dumps({"type": "chunk", "text": chunk}) + "\n"
    except Exception as e:
        err = f"❌ AI error: {e}"
        yield json.dumps({"type": "chunk", "text": err}) + "\n"
        full_response = err

    ai.conversation_history.append({"role": "assistant", "content": full_response})
    ai.save_conversation_history()

    # Store in RAG
    try:
        from jarvis_ai.config import Config
        if Config.RAG_ENABLED:
            ai.rag_engine.add_document(
                f"Q: {user_input}\nA: {full_response}",
                metadata={"type": "web_chat", "timestamp": datetime.now().isoformat()}
            )
    except Exception:
        pass

    yield json.dumps({"type": "done"}) + "\n"


@app.get("/api/chat/stream")
async def chat_stream(
    message: str,
    model: Optional[str] = None,
    agent_mode: bool = False
):
    """Server-Sent Events streaming chat endpoint."""
    async def event_generator():
        async with aclosing(
            _stream_chat_response(message, model, agent_mode, interactive=True)
        ) as events:
            async for line in events:
                yield {"data": line}

    return EventSourceResponse(event_generator())


@app.post("/api/chat")
async def chat_post(
    message: str = Form(...),
    model: Optional[str] = Form(None),
    agent_mode: bool = Form(False)
):
    """Non-streaming chat endpoint (collects full response)."""
    try:
        full = ""
        action = None
        async for line in _stream_chat_response(message, model, agent_mode):
            try:
                obj = json.loads(line.strip())
                if obj.get("type") == "chunk":
                    full += obj.get("text", "")
                elif obj.get("type") == "command_result":
                    full = obj.get("text", "")
                    action = obj.get("action")
            except Exception:
                pass
        return {"response": full, "action": action}
    except Exception as e:
        return {"response": f"❌ Error: {e}", "action": None}


@app.post("/api/voice")
async def transcribe_voice(audio: UploadFile = File(...)):
    """Transcribe audio to text using SpeechRecognition."""
    try:
        import speech_recognition as sr
        import tempfile, wave

        data = await audio.read()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_path) as source:
            audio_data = recognizer.record(source)
        os.remove(tmp_path)

        text = recognizer.recognize_google(audio_data)
        return {"text": text, "success": True}
    except Exception as e:
        return {"text": "", "success": False, "error": str(e)}


@app.post("/api/screenshot/analyze")
async def analyze_screenshot(image: UploadFile = File(...)):
    """Analyze an uploaded screenshot with AI vision."""
    try:
        import tempfile
        data = await image.read()
        suffix = Path(image.filename).suffix or ".png"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        ai = get_ai_engine()
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: ai.analyze_image(tmp_path, "Analyze this screenshot and describe what you see.")
        )
        os.remove(tmp_path)
        return {"result": result}
    except Exception as e:
        return {"result": f"❌ Error: {e}"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time bidirectional communication."""
    origin = websocket.headers.get("origin")
    expected_origin = f"http://{websocket.headers['host']}"
    if origin != expected_origin:
        await websocket.close(code=1008)
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "chat")

            if msg_type == "chat":
                user_input = data.get("message", "")
                model = data.get("model")
                agent_mode = data.get("agent_mode", False)
                device_id = data.get("device_id", "web")

                if not user_input.strip():
                    continue

                # Log to MongoDB memory
                memory_engine = get_memory_engine()
                memory_engine.remember(user_input, "Web chat processed", "web_chat", device_id)

                async with aclosing(
                    _stream_chat_response(user_input, model, agent_mode, interactive=True)
                ) as events:
                    async for line in events:
                        await websocket.send_json(json.loads(line))

            elif msg_type == "metrics":
                metrics = await get_metrics()
                await websocket.send_json({"type": "metrics", "data": metrics})

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BENX_PORT", "8000"))
    print(f"🚀 BenX Web Server starting at http://localhost:{port}")
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=False, log_level="info")

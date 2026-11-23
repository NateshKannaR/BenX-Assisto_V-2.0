"""Authenticated WebSocket endpoint for the Android companion."""

import asyncio
import os
import re
import secrets
from time import monotonic

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.websocket("/ws")
async def companion_socket(socket: WebSocket):
    token = os.environ.get("BENX_PAIRING_TOKEN", "").encode()
    if len(token) < 32 or socket.headers.get("origin"):
        await socket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await socket.accept()
    try:
        pairing = await asyncio.wait_for(socket.receive_json(), timeout=5)
        supplied = pairing.get("token") if isinstance(pairing, dict) else None
        if (
            not isinstance(supplied, str)
            or pairing.get("type") != "pair"
            or not secrets.compare_digest(supplied.encode(), token)
        ):
            await socket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        await socket.send_json({"type": "paired"})

        from jarvis_ai.command_engine import CommandEngine

        pending = None
        while True:
            message = await socket.receive_json()
            if not isinstance(message, dict):
                await socket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            kind = message.get("type")
            if kind == "confirm":
                confirmation, pending = pending, None
                if not confirmation or confirmation[0] != message.get("id") or monotonic() >= confirmation[2]:
                    result = "Confirmation expired. Request the action again."
                elif message.get("approved") is True:
                    result = await asyncio.to_thread(CommandEngine.hypr_restore_layout, confirmation[1])
                else:
                    result = "Action cancelled."
            elif kind == "battery":
                pending = None
                result = await asyncio.to_thread(CommandEngine.battery)
            elif kind == "list_layouts":
                pending = None
                result = await asyncio.to_thread(CommandEngine.hypr_list_layouts)
            elif kind == "restore_layout":
                pending = None
                name = message.get("name")
                if isinstance(name, str) and re.fullmatch(r"[\w -]{1,80}", name) and name.strip():
                    request_id = secrets.token_urlsafe(24)
                    pending = (request_id, name.strip(), monotonic() + 60)
                    await socket.send_json({
                        "type": "confirmation", "id": request_id,
                        "text": f"Restore layout '{name.strip()}' on your desktop?",
                    })
                    continue
                result = "Enter a layout name using letters, numbers, spaces, underscores or hyphens."
            else:
                pending = None
                result = "Unknown companion action."
            await socket.send_json({"type": "result", "text": result})
    except WebSocketDisconnect:
        return
    except (asyncio.TimeoutError, ValueError):
        await socket.close(code=status.WS_1008_POLICY_VIOLATION)

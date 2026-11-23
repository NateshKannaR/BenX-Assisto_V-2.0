"""Smoke tests for the local web UI and the Android companion protocol."""

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from jarvis_ai.command_engine import CommandEngine
from jarvis_ai.companion import app as companion_app
from src.main import app as web_app

TOKEN = "a" * 40


class WebTests(unittest.TestCase):
    def test_local_ui_and_socket(self):
        with TestClient(web_app, base_url="http://localhost") as client:
            for route in ("/", "/api/health", "/assets/benx.jpg"):
                self.assertEqual(client.get(route).status_code, 200)
            with client.websocket_connect("ws://localhost/ws", headers={"Origin": "http://localhost"}) as socket:
                socket.send_json({"type": "ping"})
                self.assertEqual(socket.receive_json(), {"type": "pong"})
            with self.assertRaises(WebSocketDisconnect):
                with client.websocket_connect("ws://localhost/ws", headers={"Origin": "https://example.org"}):
                    self.fail("Accepted an external origin")
            self.assertEqual(client.get("/api/health", headers={"Host": "example.org"}).status_code, 400)
            self.assertEqual(
                client.get("/api/health", headers={"Sec-Fetch-Site": "cross-site"}).status_code, 403
            )

    def test_web_confirmation(self):
        class Engine:
            conversation_history = []
            learning_engine = None

            def interpret_command(self, *args, **kwargs):
                return '{"command": "reboot"}'

        class Executor:
            @staticmethod
            def execute(command, ai, user_input, confirm):
                return "Approved" if confirm("Reboot?") else "Cancelled"

        with (
            TestClient(web_app, base_url="http://localhost") as client,
            patch("src.main.get_ai_engine", return_value=Engine()),
            patch("src.main.get_executor", return_value=Executor),
            patch("src.main.get_memory_engine"),
            client.websocket_connect("ws://localhost/ws", headers={"Origin": "http://localhost"}) as socket,
        ):
            socket.send_json({"type": "chat", "message": "reboot"})
            self.assertEqual(socket.receive_json()["type"], "status")
            self.assertEqual(socket.receive_json()["type"], "status")
            prompt = socket.receive_json()
            self.assertEqual(prompt["type"], "confirmation")
            path = f"/api/confirm/{prompt['id']}"
            self.assertEqual(client.post(path, json={"approved": True}).status_code, 204)
            self.assertEqual(socket.receive_json()["text"], "Approved")
            self.assertEqual(socket.receive_json()["type"], "done")
            self.assertEqual(client.post(path, json={"approved": True}).status_code, 404)


class CompanionTests(unittest.TestCase):
    @patch.dict(os.environ, {"BENX_PAIRING_TOKEN": TOKEN})
    def test_pairing_and_confirmed_restore(self):
        with TestClient(companion_app) as client:
            with client.websocket_connect("/ws") as socket:
                socket.send_json({"type": "pair", "token": "wrong"})
                with self.assertRaises(WebSocketDisconnect):
                    socket.receive_json()

            with (
                patch.object(CommandEngine, "hypr_restore_layout", return_value="Restored") as restore,
                client.websocket_connect("/ws") as socket,
            ):
                socket.send_json({"type": "pair", "token": TOKEN})
                self.assertEqual(socket.receive_json(), {"type": "paired"})
                socket.send_json({"type": "restore_layout", "name": "work"})
                prompt = socket.receive_json()
                self.assertEqual(prompt["type"], "confirmation")
                restore.assert_not_called()
                socket.send_json({"type": "confirm", "id": prompt["id"], "approved": True})
                self.assertEqual(socket.receive_json()["text"], "Restored")
                socket.send_json({"type": "confirm", "id": prompt["id"], "approved": True})
                self.assertIn("expired", socket.receive_json()["text"])
                restore.assert_called_once_with("work")

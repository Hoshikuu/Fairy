"""Offline tests for assistant tools, VTube Studio integration and spoken-text assets."""

import asyncio
import json
import os
import re
import struct
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fairy.ai import tools as tools_module
from fairy.ai.brain import validate_arguments
from fairy.ai.tools import assistant_tools
from fairy.desktop import vtube as vtube_module
from fairy.desktop.vtube import EXPRESSIONS, VTubeClient, compute_rms_mouth_open, vtube_tools
from fairy.paths import PROMPT, ROOT

EMOJI_OR_SYMBOL = re.compile(r"[^\x09\x0a\x0d\x20-\x7e]")


async def call(tool, arguments: dict | None = None) -> str:
    """Run a tool exactly like BrainSession: validate first, then call the handler."""
    return await tool.handler(validate_arguments(tool.parameters, arguments or {}))


def pcm(amplitude: int, samples: int = 960) -> bytes:
    """Return a square wave so the RMS equals the absolute amplitude."""
    return b"".join(struct.pack("<h", amplitude if index % 2 else -amplitude) for index in range(samples))


class AssistantToolTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.memory = Path(self.directory.name) / "memory.json"
        self.notes: list[str] = []
        self.tools = assistant_tools(memory_path=self.memory, notify=self.notes.append)

    def tearDown(self):
        self.directory.cleanup()

    def test_registered_tools_use_supported_schemas(self):
        self.assertEqual(set(self.tools), {"get_current_time", "get_active_windows", "get_system_stats",
                                           "read_clipboard", "remember_fact", "recall_facts"})
        for name, tool in self.tools.items():
            self.assertEqual(tool.name, name)
            self.assertEqual(set(tool.parameters) - {"type", "properties", "required", "additionalProperties"}, set())
            for spec in tool.parameters["properties"].values():
                self.assertEqual(set(spec) - {"type", "description", "enum"}, set(), name)
            self.assertEqual(tool.schema()["function"]["name"], name)

    async def test_current_time(self):
        data = json.loads(await call(self.tools["get_current_time"]))
        self.assertEqual(set(data), {"date", "time", "weekday", "iso"})
        moment = datetime.fromisoformat(data["iso"])
        self.assertEqual(moment.strftime("%Y-%m-%d"), data["date"])
        self.assertEqual(moment.strftime("%A"), data["weekday"])
        self.assertLess(abs((datetime.now().astimezone() - moment).total_seconds()), 60)
        with self.assertRaises(ValueError):
            await call(self.tools["get_current_time"], {"extra": "x"})

    async def test_remember_and_recall_facts_in_temporary_file(self):
        self.assertEqual(await call(self.tools["recall_facts"]), "No saved facts yet.")
        await call(self.tools["remember_fact"], {"key": "favorite game", "fact": "Celeste"})
        await call(self.tools["remember_fact"], {"key": "pet", "fact": "A cat named Miso"})
        await call(self.tools["remember_fact"], {"key": "favorite game", "fact": "Hollow Knight"})
        self.assertEqual(json.loads(await call(self.tools["recall_facts"])),
                         {"favorite game": "Hollow Knight", "pet": "A cat named Miso"})
        self.assertEqual(json.loads(self.memory.read_text(encoding="utf-8"))["pet"], "A cat named Miso")
        self.assertEqual(len(self.notes), 3)
        # A new tool set with the same storage reloads the persisted facts.
        reloaded = assistant_tools(memory_path=self.memory)
        self.assertIn("Miso", await call(reloaded["recall_facts"]))

    async def test_remember_fact_validation_and_limit(self):
        remember = self.tools["remember_fact"]
        for arguments in ({"key": " ", "fact": "x"}, {"key": "k", "fact": "  "},
                          {"key": "k" * 81, "fact": "x"}, {"key": "k", "fact": "x" * 301}):
            with self.assertRaises(ValueError):
                await call(remember, arguments)
        for arguments in ({"key": "k"}, {"key": 1, "fact": "x"}, {"key": "k", "fact": "x", "extra": "y"}):
            with self.assertRaises(ValueError):
                await call(remember, arguments)
        self.assertFalse(self.memory.exists())
        self.memory.write_text(json.dumps({f"key {index}": f"fact {index}" for index in range(100)}), encoding="utf-8")
        for index in range(100, 103):
            await call(remember, {"key": f"key {index}", "fact": f"fact {index}"})
        saved = json.loads(self.memory.read_text(encoding="utf-8"))
        self.assertEqual(len(saved), 100)
        self.assertNotIn("key 0", saved)
        self.assertNotIn("key 2", saved)
        self.assertIn("key 3", saved)
        self.assertIn("key 102", saved)

    async def test_corrupt_memory_file_is_ignored(self):
        self.memory.write_text("not json", encoding="utf-8")
        self.assertEqual(await call(self.tools["recall_facts"]), "No saved facts yet.")
        self.memory.write_text("[1, 2]", encoding="utf-8")
        self.assertEqual(await call(self.tools["recall_facts"]), "No saved facts yet.")

    async def test_system_stats_with_mocked_gpu(self):
        result = subprocess.CompletedProcess([], 0, stdout="3150, 4096, 37\n", stderr="")
        with (patch.object(tools_module.shutil, "which", return_value="nvidia-smi") as which,
              patch.object(tools_module.subprocess, "run", return_value=result) as run):
            data = json.loads(await call(self.tools["get_system_stats"]))
        which.assert_called_once_with("nvidia-smi")
        command = run.call_args.args[0]
        self.assertIn("--query-gpu=memory.used,memory.total,utilization.gpu", command)
        self.assertEqual(run.call_args.kwargs["timeout"], 2.0)
        self.assertEqual((data["vram_used_mb"], data["vram_total_mb"], data["gpu_utilization_percent"]), (3150, 4096, 37))
        for key in ("disk_total_gb", "disk_used_gb", "disk_free_gb"):
            self.assertGreaterEqual(data[key], 0)
        if os.name == "nt":
            self.assertGreater(data["ram_total_gb"], 0)
            self.assertTrue(0 <= data["ram_percent"] <= 100)

    async def test_system_stats_without_or_with_failing_gpu(self):
        with patch.object(tools_module.shutil, "which", return_value=None):
            data = json.loads(await call(self.tools["get_system_stats"]))
        self.assertNotIn("vram_used_mb", data)
        self.assertIn("disk_free_gb", data)
        with (patch.object(tools_module.shutil, "which", return_value="nvidia-smi"),
              patch.object(tools_module.subprocess, "run", side_effect=subprocess.TimeoutExpired("nvidia-smi", 2))):
            data = json.loads(await call(self.tools["get_system_stats"]))
        self.assertNotIn("vram_used_mb", data)

    async def test_windows_only_tools_fall_back_elsewhere(self):
        with patch.object(tools_module.sys, "platform", "linux"):
            windows = json.loads(await call(self.tools["get_active_windows"]))
            clipboard = await call(self.tools["read_clipboard"])
        self.assertEqual((windows["active_window"], windows["open_windows"]), ("", []))
        self.assertIn("only available on Windows", clipboard)

    @unittest.skipUnless(os.name == "nt", "Window inspection uses user32")
    async def test_active_windows_is_bounded_json(self):
        data = json.loads(await call(self.tools["get_active_windows"]))
        self.assertIsInstance(data["active_window"], str)
        self.assertLessEqual(len(data["open_windows"]), 15)
        self.assertEqual(len(data["open_windows"]), len(set(data["open_windows"])))


class MouthOpenTests(unittest.TestCase):
    def test_silence_and_empty_audio_close_the_mouth(self):
        self.assertEqual(compute_rms_mouth_open(b""), 0.0)
        self.assertEqual(compute_rms_mouth_open(b"\x01"), 0.0)
        self.assertEqual(compute_rms_mouth_open(bytes(3840)), 0.0)
        self.assertEqual(compute_rms_mouth_open(pcm(150)), 0.0)

    def test_loud_audio_opens_the_mouth_within_range(self):
        self.assertEqual(compute_rms_mouth_open(pcm(30000)), 1.0)
        medium = compute_rms_mouth_open(pcm(3000))
        quiet = compute_rms_mouth_open(pcm(1000))
        self.assertTrue(0.0 < quiet < medium < 1.0)
        self.assertEqual(compute_rms_mouth_open(pcm(3000) + b"\x01"), medium)


class FakeSocket:
    """Minimal VTube Studio Public API v1.0 responder."""

    def __init__(self, hotkeys: list[dict]):
        self.hotkeys = hotkeys
        self.sent: list[dict] = []
        self.closed = False
        self.replies: asyncio.Queue = asyncio.Queue()

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)
        kind = payload["messageType"]
        data = {}
        if kind == "AuthenticationTokenRequest":
            data = {"authenticationToken": "secret-token"}
        elif kind == "AuthenticationRequest":
            data = {"authenticated": payload["data"]["authenticationToken"] == "secret-token"}
        elif kind == "HotkeysInCurrentModelRequest":
            data = {"availableHotkeys": self.hotkeys}
        await self.replies.put({"apiName": "VTubeStudioPublicAPI", "apiVersion": "1.0",
                                "requestID": payload["requestID"],
                                "messageType": kind.replace("Request", "Response"), "data": data})

    async def receive_json(self, timeout: float | None = None) -> dict:
        return await asyncio.wait_for(self.replies.get(), timeout)

    async def close(self) -> None:
        self.closed = True


class FakeSession:
    instances: list["FakeSession"] = []

    def __init__(self, socket: FakeSocket | None = None, **kwargs):
        self.socket = socket
        self.kwargs = kwargs
        self.urls: list[str] = []
        self.closed = False
        FakeSession.instances.append(self)

    async def ws_connect(self, url: str, **_kwargs):
        self.urls.append(url)
        if self.socket is None:
            raise OSError("connection refused")
        return self.socket

    async def close(self) -> None:
        self.closed = True


class VTubeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.token = Path(self.directory.name) / "vtube_token"
        FakeSession.instances.clear()

    def tearDown(self):
        self.directory.cleanup()

    def test_only_local_websocket_urls_are_accepted(self):
        for url in ("ws://127.0.0.1:8001", "ws://localhost:8001", "ws://127.0.0.1:9000/"):
            self.assertEqual(VTubeClient(url, token_path=self.token).url, url)
        for url in ("ws://example.com:8001", "wss://127.0.0.1:8001", "http://127.0.0.1:8001",
                    "ws://user:pw@127.0.0.1:8001", "ws://127.0.0.1:8001/api", "ws://127.0.0.1:8001?x=1",
                    "ws://192.168.1.5:8001"):
            with self.assertRaises(ValueError, msg=url):
                VTubeClient(url, token_path=self.token)
        with patch.dict(os.environ, {"FAIRY_VTUBE_URL": "ws://example.com:8001"}):
            with self.assertRaises(ValueError):
                VTubeClient(token_path=self.token)
        env = {key: value for key, value in os.environ.items() if key != "FAIRY_VTUBE_URL"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(VTubeClient(token_path=self.token).url, "ws://127.0.0.1:8001")

    async def test_constructor_has_no_network_or_disk_side_effects(self):
        with patch.object(vtube_module.aiohttp, "ClientSession") as session:
            client = VTubeClient("ws://127.0.0.1:8001", token_path=self.token)
            await client.close()
        session.assert_not_called()
        self.assertFalse(self.token.exists())

    async def test_unavailable_vtube_studio_fails_gracefully(self):
        client = VTubeClient("ws://127.0.0.1:8001", token_path=self.token)
        with patch.object(vtube_module.aiohttp, "ClientSession", FakeSession):
            self.assertFalse(await client.connect())
            self.assertFalse(await client.set_mouth_open(0.5))
            self.assertFalse(await client.trigger_hotkey("happy"))
            self.assertEqual(await client.set_expression("happy"), "VTube Studio is not running or unavailable.")
            await client.close()
        self.assertTrue(FakeSession.instances)
        for session in FakeSession.instances:
            self.assertIs(session.kwargs["trust_env"], False)
            self.assertIsNotNone(session.kwargs.get("timeout"))
            self.assertTrue(session.closed)
            self.assertEqual(session.urls, ["ws://127.0.0.1:8001"])
        self.assertFalse(self.token.exists())

    async def test_protocol_authenticates_injects_mouth_and_triggers_hotkey(self):
        socket = FakeSocket([{"name": "Smug Face", "type": "ToggleExpression", "hotkeyID": "id-smug"},
                             {"name": "happy", "type": "ToggleExpression", "hotkeyID": "id-happy"}])
        client = VTubeClient("ws://127.0.0.1:8001", token_path=self.token)
        with patch.object(vtube_module.aiohttp, "ClientSession", lambda **kwargs: FakeSession(socket, **kwargs)):
            self.assertTrue(await client.connect())
            self.assertTrue(await client.set_mouth_open(1.7))
            self.assertEqual(await client.set_expression("happy"), "Expression set to happy.")
            self.assertEqual(await client.set_expression("smug"), "Expression set to smug.")
            self.assertIn("No matching hotkey", await client.set_expression("sad"))
            await client.close()
        self.assertEqual(self.token.read_text(encoding="utf-8"), "secret-token")
        self.assertTrue(socket.closed)
        for payload in socket.sent:
            self.assertEqual((payload["apiName"], payload["apiVersion"]), ("VTubeStudioPublicAPI", "1.0"))
            self.assertTrue(payload["requestID"])
        kinds = [payload["messageType"] for payload in socket.sent]
        self.assertEqual(kinds[:2], ["AuthenticationTokenRequest", "AuthenticationRequest"])
        inject = next(payload["data"] for payload in socket.sent if payload["messageType"] == "InjectParameterDataRequest")
        self.assertEqual(inject, {"parameterValues": [{"id": "MouthOpen", "value": 1.0}], "mode": "set"})
        triggered = [payload["data"]["hotkeyID"] for payload in socket.sent if payload["messageType"] == "HotkeyTriggerRequest"]
        self.assertEqual(triggered, ["id-happy", "id-smug"])

    async def test_saved_token_skips_token_request(self):
        self.token.write_text("secret-token", encoding="utf-8")
        socket = FakeSocket([])
        client = VTubeClient("ws://127.0.0.1:8001", token_path=self.token)
        with patch.object(vtube_module.aiohttp, "ClientSession", lambda **kwargs: FakeSession(socket, **kwargs)):
            self.assertTrue(await client.connect())
            await client.close()
        self.assertEqual([payload["messageType"] for payload in socket.sent], ["AuthenticationRequest"])

    async def test_set_expression_tool_validation(self):
        client = MagicMock()
        client.set_expression = AsyncMock(return_value="Expression set to smug.")
        notes: list[str] = []
        tool = vtube_tools(client, notify=notes.append)["set_expression"]
        self.assertEqual(tool.parameters["properties"]["expression"]["enum"], list(EXPRESSIONS))
        self.assertEqual(set(EXPRESSIONS), {"happy", "smug", "flustered", "angry", "surprised", "sad", "neutral"})
        self.assertEqual(await call(tool, {"expression": "smug"}), "Expression set to smug.")
        client.set_expression.assert_awaited_once_with("smug")
        self.assertEqual(notes, ["smug"])
        for arguments in ({"expression": "excited"}, {"expression": 1}, {}, {"expression": "happy", "x": 1}):
            with self.assertRaises(ValueError):
                await call(tool, arguments)
        with self.assertRaises(ValueError):
            await tool.handler({"expression": "excited"})
        with self.assertRaises(ValueError):
            await VTubeClient("ws://127.0.0.1:8001", token_path=self.token).set_expression("excited")
        self.assertEqual(client.set_expression.await_count, 1)


class SpokenAssetTests(unittest.TestCase):
    def test_system_prompt_is_clean_english(self):
        text = PROMPT.read_text(encoding="utf-8")
        self.assertIsNone(EMOJI_OR_SYMBOL.search(text))
        for symbol in ("~", "*", "#", "`", "_", "|", "<", ">"):
            self.assertNotIn(symbol, text)
        lowered = text.lower()
        for name in ("hu tao", "minato", "aqua", "genshin", "hololive"):
            self.assertNotIn(name, lowered)
        self.assertIn("Fairy", text)
        self.assertIn("English", text)

    def test_desktop_interface_has_no_emojis_and_keeps_contract(self):
        for name in ("index.html", "renderer.js", "style.css", "main.js"):
            text = (ROOT / "desktop" / name).read_text(encoding="utf-8")
            match = EMOJI_OR_SYMBOL.search(text)
            self.assertIsNone(match, f"{name}: {match and repr(match.group())}")
        html = (ROOT / "desktop" / "index.html").read_text(encoding="utf-8")
        for element in ("dot", "status", "screen", "control", "vtube", "reset", "activity", "messages",
                        "input", "send", "mic", "stop", "picker", "sources", "close-picker"):
            self.assertIn(f'id="{element}"', html)
        self.assertIn("default-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
                      "style-src 'self'; script-src 'self'", html)
        self.assertNotIn("<aside", html)
        self.assertIn("VTube: off", html)
        main = (ROOT / "desktop" / "main.js").read_text(encoding="utf-8")
        for setting in ("contextIsolation: true", "nodeIntegration: false", "sandbox: true"):
            self.assertIn(setting, main)


if __name__ == "__main__":
    unittest.main()

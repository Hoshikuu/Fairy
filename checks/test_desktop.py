"""Desktop session and bridge behavior without hardware or models."""

import asyncio
import base64
import io
import json
import unittest
from unittest.mock import AsyncMock

from fairy.desktop.bridge import Bridge
from fairy.desktop.session import DesktopSession


class DesktopTests(unittest.IsolatedAsyncioTestCase):
    async def test_turn_transcribes_speaks_and_cancel_restores_history(self):
        omni = AsyncMock()
        omni.transcribe.return_value = "Hello"
        omni.speak = AsyncMock()
        session = DesktopSession(omni, "prompt")
        session.brain.respond_text = AsyncMock(return_value="Hi")
        result = await session.respond(pcm=b"\0\0", on_audio=AsyncMock())
        self.assertEqual(result, "Hi")
        session.brain.respond_text.assert_awaited_once_with("Unverified ASR transcript: Hello")
        omni.speak.assert_awaited_once()

        session.brain.history = [{"role": "user", "content": "previous"}]
        started = asyncio.Event()
        async def slow(_text):
            session.brain.history.append({"role": "user", "content": "partial"})
            started.set()
            await asyncio.Event().wait()
        session.brain.respond_text = slow
        task = asyncio.create_task(session.respond(text="test", on_audio=AsyncMock()))
        await started.wait()
        await session.cancel()
        await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(session.brain.history, [{"role": "user", "content": "previous"}])
        await session.close()

    async def test_bridge_validates_screen_and_resets(self):
        bridge = Bridge(io.StringIO())
        frame = base64.b64encode(b"\xff\xd8\xfftest\xff\xd9").decode()
        await bridge.command({"type": "frame", "data": frame})
        self.assertEqual(bridge.current_frame(), frame)
        await bridge.command({"type": "clear_frame"})
        self.assertIsNone(bridge.current_frame())
        with self.assertRaises(ValueError):
            await bridge.command({"type": "frame", "data": base64.b64encode(b"bad").decode()})
        bridge.emit("status", message="ready")
        self.assertEqual(json.loads(bridge.output.getvalue())["message"], "ready")

    async def test_concurrent_turn_rejected(self):
        session = DesktopSession(AsyncMock(), "prompt")
        started = asyncio.Event()
        async def slow(_text):
            started.set()
            await asyncio.Event().wait()
        session.brain.respond_text = slow
        first = asyncio.create_task(session.respond(text="first", on_audio=AsyncMock()))
        await started.wait()
        with self.assertRaises(RuntimeError):
            await session.respond(text="second", on_audio=AsyncMock())
        await session.cancel()
        await asyncio.gather(first, return_exceptions=True)
        await session.close()

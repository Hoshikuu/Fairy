import asyncio
import base64
import unittest
from unittest.mock import AsyncMock

from fairy.voice.dual import DualVoiceClient
from fairy.ai.screen import screen_tool


class DualVoiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_screen_tool_routes_targeted_analysis_and_expires(self):
        omni = AsyncMock()
        omni.describe.return_value = "Visible error: connection refused"
        frame = base64.b64encode(b"jpeg").decode()
        tool = screen_tool(omni, lambda: frame)
        output = await tool.handler({"question": "What error is visible?"})
        omni.describe.assert_awaited_once_with([(b"jpeg", "image/jpeg")], "What error is visible?")
        self.assertIn("LFM3 analysis", output)
        frame = None
        self.assertIn("no longer available", await tool.handler({"question": "Read it"}))
        self.assertEqual(omni.describe.await_count, 1)

    async def test_screen_tool_is_available_only_for_current_voice_turn(self):
        omni = AsyncMock()
        omni.transcribe.return_value = "What is on my screen?"
        omni.describe.return_value = "A red page"
        client = DualVoiceClient(omni, "system")
        async def answer(text):
            self.assertIn("view_screen", client.brain.tools)
            await client.brain.tools["view_screen"].handler({"question": text})
            return "A red page"
        client.brain.respond_text = answer
        await client.respond(b"\0\0", AsyncMock(), screen_frame=lambda: base64.b64encode(b"jpeg").decode())
        self.assertEqual(client.brain.tools, {})
        omni.speak.assert_awaited_once()

    async def test_routes_transcript_and_speaks_final_answer(self):
        omni = AsyncMock()
        omni.transcribe.return_value = "hello"
        client = DualVoiceClient(omni, "system")
        client.brain.respond_text = AsyncMock(return_value="Hello back")
        callback = AsyncMock()
        result = await client.respond(b"\0\0", callback)
        self.assertEqual(result, "Hello back")
        self.assertIn("Unverified ASR transcript", client.brain.respond_text.await_args.args[0])
        omni.speak.assert_awaited_once_with("Hello back", callback)

    async def test_interrupt_cancels_and_restores_context(self):
        omni = AsyncMock()
        started = asyncio.Event()
        async def speak(text, callback):
            started.set()
            await asyncio.Event().wait()
        omni.speak.side_effect = speak
        client = DualVoiceClient(omni, "system")
        async def answer(text):
            client.brain.history.append({"role": "user", "content": text})
            return "answer"
        client.brain.respond_text = answer
        turn = asyncio.create_task(client.respond_spoken_text("hello", AsyncMock()))
        await started.wait()
        await client.cancel()
        self.assertEqual(await turn, "")
        self.assertEqual(client.brain.history, [])


if __name__ == "__main__":
    unittest.main()

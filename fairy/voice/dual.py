"""Adapt the separate ASR, conversation and speech stages to voice sessions."""

import asyncio
import time
import logging

from fairy.ai.brain import BrainConfig, BrainSession
from fairy.ai.screen import SCREEN_TOOL_INSTRUCTIONS, screen_tool
from fairy.realtime.omni import OmniClient

log = logging.getLogger(__name__)


class DualVoiceClient:
    input_rate = 16000
    output_rate = 24000

    def __init__(self, omni: OmniClient, instructions: str):
        self.omni = omni
        self.brain = BrainSession(BrainConfig.from_env(), instructions)
        self.task: asyncio.Task | None = None

    async def connect(self):
        return None

    async def close(self):
        await self.cancel()
        await self.brain.close()

    async def cancel(self):
        if self.task and not self.task.done():
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)

    async def _run(self, text: str, on_audio):
        previous = list(self.brain.history)
        try:
            answer = await self.brain.respond_text(text)
            await self.omni.speak(answer, on_audio)
            return answer
        except BaseException:
            self.brain.history[:] = previous
            raise

    async def _execute(self, operation):
        self.task = asyncio.create_task(operation)
        try:
            return await asyncio.shield(self.task)
        except asyncio.CancelledError:
            if self.task.cancelled():
                return ""
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            raise
        finally:
            self.task = None

    async def respond(self, pcm: bytes, on_audio, *, screen_frame=None):
        async def turn():
            started = time.monotonic()
            transcript = await self.omni.transcribe(pcm)
            previous_tools = self.brain.tools
            previous_instructions = self.brain.instructions
            try:
                if screen_frame is not None and screen_frame():
                    self.brain.tools = {**previous_tools, "view_screen": screen_tool(self.omni, screen_frame)}
                    self.brain.instructions += SCREEN_TOOL_INSTRUCTIONS
                answer = await self._run("Unverified ASR transcript of this user's speech: " + transcript, on_audio)
                log.info("Voice response completed in %.2fs", time.monotonic() - started)
                return answer
            finally:
                self.brain.tools = previous_tools
                self.brain.instructions = previous_instructions
        return await self._execute(turn())

    async def respond_spoken_text(self, text: str, on_audio):
        return await self._execute(self._run(text, on_audio))

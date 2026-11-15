"""A single local desktop conversation independent of Discord."""

import asyncio
import re
from collections.abc import Awaitable, Callable

from fairy.ai.brain import BrainConfig, BrainSession
from fairy.ai.screen import SCREEN_TOOL_INSTRUCTIONS, screen_tool
from fairy.realtime.omni import OmniClient

MIN_SPEECH_FRAGMENT = 20


def split_speech_sentences(text: str) -> list[str]:
    """Split a reply into sentences for TTS, merging fragments that are too short."""
    text = text.strip()
    merged: list[str] = []
    pending = ""
    for part in re.split(r"(?<=[.!?])\s+", text):
        pending = f"{pending} {part}".strip()
        if len(pending) >= MIN_SPEECH_FRAGMENT:
            merged.append(pending)
            pending = ""
    if pending:
        if merged:
            merged[-1] = f"{merged[-1]} {pending}"
        else:
            merged.append(pending)
    return merged or [text]


class DesktopSession:
    """Coordinate text, microphone audio, screen observations and speech."""

    def __init__(self, omni: OmniClient, instructions: str) -> None:
        self.omni = omni
        self.brain = BrainSession(BrainConfig.from_env(), instructions)
        self.task: asyncio.Task[str] | None = None

    async def close(self) -> None:
        await self.cancel()
        await self.brain.close()
        await self.omni.close()

    async def cancel(self) -> None:
        task = self.task
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def respond(
        self,
        *,
        text: str | None = None,
        pcm: bytes | None = None,
        on_audio: Callable[[bytes], Awaitable[None]],
        frame_provider: Callable[[], str | None] | None = None,
    ) -> str:
        if self.task is not None:
            raise RuntimeError("A desktop turn is already running")
        if (text is None) == (pcm is None):
            raise ValueError("Provide exactly one of text or microphone audio")

        async def turn() -> str:
            history = list(self.brain.history)
            tools = self.brain.tools
            instructions = self.brain.instructions
            try:
                message = text
                if pcm is not None:
                    message = "Unverified ASR transcript: " + await self.omni.transcribe(pcm)
                if not message or not message.strip():
                    raise ValueError("Empty message")
                if frame_provider is not None and frame_provider():
                    self.brain.tools = {**tools, "view_screen": screen_tool(self.omni, frame_provider)}
                    self.brain.instructions += SCREEN_TOOL_INSTRUCTIONS
                answer = await self.brain.respond_text(message)
                for sentence in split_speech_sentences(answer):
                    await self.omni.speak(sentence, on_audio)
                return answer
            except BaseException:
                self.brain.history[:] = history
                raise
            finally:
                self.brain.tools = tools
                self.brain.instructions = instructions

        self.task = asyncio.create_task(turn())
        try:
            return await self.task
        finally:
            self.task = None

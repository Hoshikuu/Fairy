"""Async Kokoro HTTP client and Discord's 48 kHz stereo PCM transport."""

from __future__ import annotations

import asyncio
import audioop
import io
import re
import wave

import discord
import httpx

FRAME_BYTES = 3840  # 20 ms, 48 kHz, two channels, signed 16-bit PCM.
MAX_WAV_BYTES = 32 * 1024 * 1024


async def check_kokoro(*, server_url="http://127.0.0.1:8082", voice=None):
    async with httpx.AsyncClient(timeout=httpx.Timeout(5, connect=3), trust_env=False) as client:
        response = await client.get(f"{server_url.rstrip('/')}/health")
        response.raise_for_status()
        health = response.json()
        if health.get("status") != "ok" or health.get("model") != "kokoro":
            raise ValueError("The configured endpoint is not a ready Kokoro service")
        if voice and health.get("voice") != voice:
            raise ValueError("KOKORO_VOICE does not match the voice configured in llama_start.py")


def speech_chunks(text: str):
    """Split long LLM answers at sentence boundaries to fit the service limit."""
    remaining = text.strip()
    while remaining:
        end = min(len(remaining), 1000)
        if end < len(remaining):
            boundaries = list(re.finditer(r"[.!?]\s+|\n+", remaining[:end]))
            boundary = boundaries[-1].end() if boundaries else remaining.rfind(" ", 0, end)
            if boundary > 0:
                end = boundary
        chunk, remaining = remaining[:end].strip(), remaining[end:].lstrip()
        if chunk:
            yield chunk


async def synthesize_wav(text: str, *, server_url="http://127.0.0.1:8082", voice=None, speed=1.0) -> bytes:
    payload = {"model": "kokoro", "input": text, "speed": speed, "response_format": "wav"}
    if voice:
        payload["voice"] = voice
    async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=3), trust_env=False) as client:
        async with client.stream("POST", f"{server_url.rstrip('/')}/v1/audio/speech", json=payload) as response:
            response.raise_for_status()
            if response.headers.get("content-type", "").split(";", 1)[0] != "audio/wav":
                raise ValueError("Kokoro did not return a WAV")
            audio = bytearray()
            async for chunk in response.aiter_bytes():
                audio.extend(chunk)
                if len(audio) > MAX_WAV_BYTES:
                    raise ValueError("Kokoro WAV is too large")
    return bytes(audio)


class DiscordPCM(discord.AudioSource):
    def __init__(self, wav: bytes):
        with wave.open(io.BytesIO(wav), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 24000):
                raise ValueError("Expected mono PCM16 WAV at 24 kHz from Kokoro")
            mono = audio.readframes(audio.getnframes())
            if not mono or len(mono) != audio.getnframes() * 2:
                raise ValueError("Kokoro returned empty or incomplete audio")
        converted, _ = audioop.ratecv(mono, 2, 1, 24000, 48000, None)
        self.pcm = audioop.tostereo(converted, 2, 1, 1)
        self.duration = len(self.pcm) / (48000 * 2 * 2)
        self.offset = 0

    def read(self) -> bytes:
        frame = self.pcm[self.offset:self.offset + FRAME_BYTES]
        self.offset += FRAME_BYTES
        return frame.ljust(FRAME_BYTES, b"\0") if frame else b""

    def is_opus(self) -> bool:
        return False

    def cleanup(self):
        self.pcm = b""


async def play_wav(voice_client, wav: bytes):
    source = await asyncio.to_thread(DiscordPCM, wav)
    loop = asyncio.get_running_loop()
    completed = loop.create_future()

    def finish(error):
        if not completed.done():
            if error:
                completed.set_exception(error)
            else:
                completed.set_result(None)

    def after(error):
        # discord.py runs playback and its completion callback on another thread.
        try:
            loop.call_soon_threadsafe(finish, error)
        except RuntimeError:
            pass  # The event loop may close while the playback thread exits.

    try:
        voice_client.play(source, after=after)
        await asyncio.wait_for(completed, timeout=source.duration + 10)
    finally:
        if getattr(voice_client, "source", None) is source:
            # VoiceRecvClient.stop() also stops the microphone receiver.
            voice_client.stop_playing()
        source.cleanup()

"""LFM3 task-specific inference through the local llama.cpp server."""

import asyncio
import base64
import io
import logging
import os
import time
import wave
from pathlib import Path
from urllib.parse import urlsplit

import aiohttp

from fairy.paths import OMNI_MODEL

log = logging.getLogger(__name__)


class OmniError(RuntimeError):
    pass


class OmniClient:
    """Share one client and semaphore between all LFM3 operations."""

    input_rate = 16000
    output_rate = 24000

    def __init__(self, url: str, *, asr_language: str = "English",
                 tts_language: str = "English", voice: str = "female",
                 timeout: float = 180, concurrency: int = 1):
        parts = urlsplit(url)
        if (parts.scheme != "http" or parts.hostname not in ("localhost", "127.0.0.1")
                or parts.username or parts.password or parts.path not in ("", "/")
                or parts.query or parts.fragment):
            raise ValueError("Omni server must be a local HTTP origin")
        if voice not in ("female", "male") or concurrency < 1 or timeout <= 0:
            raise ValueError("Invalid Omni configuration")
        self.url = f"http://{parts.netloc}"
        self.asr_language = asr_language
        self.tts_language = tts_language
        self.voice = voice
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client = None

    @property
    def model_name(self) -> str:
        return Path(os.getenv("FAIRY_OMNI_MODEL_PATH", str(OMNI_MODEL))).name

    async def connect(self):
        if self.client is None or self.client.closed:
            self.client = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout), trust_env=False)

    async def close(self):
        if self.client is not None:
            await self.client.close()
            self.client = None

    async def _chat(self, system: str, content: list, *, task: str) -> str:
        await self.connect()
        queued = time.monotonic()
        async with self.semaphore:
            start = time.monotonic()
            print(f"[{self.model_name}][PROCESSING] {task}", flush=True)
            async with self.client.post(self.url + "/v1/chat/completions", json={
                "model": "local", "temperature": 0, "max_tokens": 1024,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": content}],
            }) as response:
                response.raise_for_status()
                result = await response.json()
            log.info("LFM3 inference %.2fs (queue %.2fs)", time.monotonic() - start, start - queued)
        try:
            text = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise OmniError("Invalid LFM3 response") from error
        if not isinstance(text, str) or not text.strip():
            raise OmniError("LFM3 returned no text")
        print(f"[{self.model_name}][OUTPUT][{task}] {text.strip()}", flush=True)
        return text.strip()

    async def transcribe(self, pcm: bytes) -> str:
        if not pcm or len(pcm) % 2:
            raise ValueError("Expected nonempty PCM16 mono audio")
        data = io.BytesIO()
        with wave.open(data, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(self.input_rate)
            wav.writeframes(pcm)
        encoded = base64.b64encode(data.getvalue()).decode("ascii")
        return await self._chat(f"Perform ASR in {self.asr_language}.", [
            {"type": "input_audio", "input_audio": {"data": encoded, "format": "wav"}}
        ], task="ASR")

    async def describe(self, images: list[tuple[bytes, str]], question: str) -> str:
        if not images:
            raise ValueError("At least one image is required")
        content = [{"type": "text", "text": question or "Describe the image."}]
        for data, mime in images:
            if not data or mime not in ("image/jpeg", "image/png", "image/webp"):
                raise ValueError("Invalid image")
            encoded = base64.b64encode(data).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}})
        return await self._chat(
            "Analyze the images for the user's question. Report visible facts and exact readable text, "
            "identify uncertainty, and do not invent details. Respond in text.", content, task="Vision")

    async def speak(self, text: str, on_audio):
        if not text.strip():
            raise ValueError("Cannot synthesize empty text")
        await self.connect()
        queued = time.monotonic()
        async with self.semaphore:
            start = time.monotonic()
            print(f"[{self.model_name}][PROCESSING] TTS", flush=True)
            async with asyncio.timeout(self.timeout):
                async with self.client.ws_connect(self.url + "/v1/realtime") as ws:
                    created = await ws.receive_json()
                    if created.get("type") != "session.created":
                        raise OmniError("LFM3 realtime session failed")
                    rate = created.get("session", {}).get("audio", {}).get("output", {}).get("format", {}).get("rate", self.output_rate)
                    if rate != self.output_rate:
                        raise OmniError(f"Unexpected LFM3 output sample rate: {rate}")
                    await ws.send_json({"type": "session.update", "session": {
                        "type": "realtime", "instructions": f"Perform TTS in {self.tts_language} using a {self.voice} voice.",
                        "output_modalities": ["audio"]}})
                    updated = await ws.receive_json()
                    if updated.get("type") != "session.updated":
                        raise OmniError("LFM3 realtime configuration failed")
                    await ws.send_json({"type": "conversation.item.create", "item": {
                        "type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]}})
                    await ws.send_json({"type": "response.create"})
                    received = False
                    async for message in ws:
                        if message.type != aiohttp.WSMsgType.TEXT:
                            continue
                        event = message.json()
                        kind = event.get("type")
                        if kind == "error":
                            raise OmniError("LFM3 speech generation failed")
                        if kind == "response.output_audio.delta":
                            chunk = base64.b64decode(event["delta"], validate=True)
                            if len(chunk) % 2:
                                raise OmniError("Invalid LFM3 PCM audio")
                            if chunk:
                                received = True
                                await on_audio(chunk)
                        elif kind == "response.done":
                            status = event.get("response", {}).get("status")
                            if status not in (None, "completed") or not received:
                                raise OmniError("LFM3 speech generation did not complete")
                            break
                    else:
                        raise OmniError("LFM3 speech stream closed unexpectedly")
            log.info("LFM3 speech %.2fs (queue %.2fs)", time.monotonic() - start, start - queued)

"""Kokoro HTTP health and synthesis client."""

from __future__ import annotations

import httpx

MAX_WAV_BYTES = 32 * 1024 * 1024


async def check_kokoro(*, server_url="http://127.0.0.1:8082", voice=None):
    async with httpx.AsyncClient(timeout=httpx.Timeout(5, connect=3), trust_env=False) as client:
        response = await client.get(f"{server_url.rstrip('/')}/health")
        response.raise_for_status()
        health = response.json()
        if health.get("status") != "ok" or health.get("model") != "kokoro":
            raise ValueError("The configured endpoint is not a ready Kokoro service")
        if voice and health.get("voice") != voice:
            raise ValueError("KOKORO_VOICE does not match the voice configured in fairy/start.py")


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

"""Whisper HTTP transcription clients."""

from __future__ import annotations

import io
import json
import urllib.request
import uuid
import wave
from pathlib import Path
import httpx


async def transcribe_pcm(
    pcm: bytes,
    *,
    server_url: str = "http://127.0.0.1:8081",
    language: str = "en",
) -> str:
    """Transcribe mono 16 kHz, signed 16-bit PCM without keeping audio files."""
    if not pcm or len(pcm) % 2:
        raise ValueError("Expected non-empty, 16-bit PCM audio")
    if len(pcm) > 25 * 1024 * 1024:
        raise ValueError("Audio is larger than the 25 MiB client limit")
    wav_data = io.BytesIO()
    with wave.open(wav_data, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(pcm)
    async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=3), trust_env=False) as client:
        response = await client.post(
            server_url.rstrip("/") + "/inference",
            data={"response_format": "json", "language": language},
            files={"file": ("audio.wav", wav_data.getvalue(), "audio/wav")},
        )
        response.raise_for_status()
        result = response.json()
    if not isinstance(result.get("text"), str):
        raise RuntimeError("Whisper returned no transcription")
    return result["text"].strip()


def transcribe_wav(
    path: str | Path,
    *,
    server_url: str = "http://127.0.0.1:8081",
    language: str = "en",
) -> str:
    audio = Path(path)
    with wave.open(str(audio), "rb") as wav:
        if (wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getcomptype()) != (
            1, 16000, 2, "NONE"
        ):
            raise ValueError("Audio must be mono 16 kHz, 16-bit PCM WAV")
    if audio.stat().st_size > 25 * 1024 * 1024:
        raise ValueError("Audio file is larger than the 25 MiB client limit")

    boundary = uuid.uuid4().hex
    fields = {"response_format": "json", "language": language}
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
        b"Content-Type: audio/wav\r\n\r\n"
    )
    body.extend(audio.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    request = urllib.request.Request(
        server_url.rstrip("/") + "/inference",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        result = json.load(response)
    if "text" not in result:
        raise RuntimeError(f"Whisper returned no transcription: {result}")
    return result["text"].strip()

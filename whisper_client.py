"""Minimal WAV client for Fairy's whisper-server.

From Python: ``text = transcribe_wav('audio.wav')``.
From a terminal: ``python whisper_client.py audio.wav``.
The WAV must contain mono, 16 kHz, 16-bit PCM audio.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
import uuid
import wave
from pathlib import Path


def transcribe_wav(
    path: str | Path,
    *,
    server_url: str = "http://127.0.0.1:8081",
    language: str = "auto",
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--language", default="auto")
    args = parser.parse_args()
    print(transcribe_wav(args.wav, server_url=args.url, language=args.language))


if __name__ == "__main__":
    main()

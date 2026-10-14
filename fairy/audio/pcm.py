"""Convert Kokoro WAV audio into Discord PCM frames."""

from __future__ import annotations

import audioop
import io
import wave
import discord

FRAME_BYTES = 3840  # 20 ms, 48 kHz, two channels, signed 16-bit PCM.


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

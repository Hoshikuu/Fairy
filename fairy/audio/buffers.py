"""Per-speaker PCM state and completed utterances."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SpeakerBuffer:
    pcm: bytearray = field(default_factory=bytearray)
    resample_state: object = None
    last_voice: float = 0
    voiced_bytes: int = 0


@dataclass(frozen=True)
class Utterance:
    user_id: int
    pcm: bytes

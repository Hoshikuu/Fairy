"""Environment settings loaded when constructing the Discord app."""
from dataclasses import dataclass
import math
import os
from dotenv import load_dotenv
from .paths import PROJECT_ROOT

@dataclass(frozen=True)
class BotSettings:
    token: str | None = None
    whisper_url: str = "http://127.0.0.1:8081"
    whisper_language: str = "en"
    kokoro_url: str = "http://127.0.0.1:8082"
    kokoro_voice: str | None = None
    kokoro_speed: float = 1.0

    @classmethod
    def from_env(cls):
        load_dotenv(PROJECT_ROOT / ".env")
        speed = float(os.getenv("KOKORO_SPEED", "1.0"))
        if not math.isfinite(speed) or not 0.5 <= speed <= 2.0:
            raise ValueError("KOKORO_SPEED must be between 0.5 and 2.0")
        return cls(token=os.getenv("TOKEN"),
                   whisper_url=os.getenv("WHISPER_URL", "http://127.0.0.1:8081"),
                   kokoro_url=os.getenv("KOKORO_URL", "http://127.0.0.1:8082"),
                   kokoro_voice=os.getenv("KOKORO_VOICE") or None, kokoro_speed=speed)

"""Persistent local Kokoro service with an OpenAI-style speech endpoint."""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
import io
import logging
from pathlib import Path
import threading
from typing import Literal
import os

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parent
log = logging.getLogger(__name__)


class SpeechRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: Literal["kokoro"] = "kokoro"
    input: str = Field(min_length=1, max_length=4000)
    voice: str | None = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0, allow_inf_nan=False)
    response_format: Literal["wav"] = "wav"

    @field_validator("input")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("input must contain text")
        return value


class KokoroEngine:
    def __init__(self, voice="af_heart", device="cpu", threads=4):
        self.voice = voice
        self.device = device
        self.threads = threads
        self.pipeline = None
        self.lock = threading.Lock()

    def load(self):
        # Keep weights under the project, shared by setup and server processes.
        os.environ.setdefault("HF_HOME", str(ROOT / "models" / "kokoro"))
        import torch
        from kokoro import KPipeline

        torch.set_num_threads(self.threads)
        self.pipeline = KPipeline(
            lang_code=self.voice[0], repo_id="hexgrad/Kokoro-82M", device=self.device
        )
        self.synthesize("Hello. The voice service is ready.", self.voice, 1.0)

    def synthesize(self, text: str, voice: str, speed: float) -> bytes:
        import numpy as np
        import soundfile as sf
        import torch

        if self.pipeline is None:
            raise RuntimeError("Kokoro is not loaded")
        with self.lock, torch.inference_mode():
            chunks = [
                result.audio.detach().cpu().numpy()
                for result in self.pipeline(text, voice=voice, speed=speed)
                if result.audio is not None
            ]
            if not chunks:
                raise ValueError("The text produced no speech")
            output = io.BytesIO()
            sf.write(output, np.concatenate(chunks), 24000, format="WAV", subtype="PCM_16")
            return output.getvalue()


def create_app(engine: KokoroEngine) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        # Startup completes only after model loading and warmup succeed.
        engine.load()
        yield
        engine.pipeline = None

    app = FastAPI(title="Fairy Kokoro TTS", lifespan=lifespan)
    # At most one synthesis and two waiting requests. The threading lock keeps
    # inference serialized even when an HTTP client cancels its request.
    capacity = threading.BoundedSemaphore(3)

    @app.get("/health")
    def health():
        if engine.pipeline is None:
            raise HTTPException(503, "Kokoro is loading")
        return {"status": "ok", "model": "kokoro", "voice": engine.voice,
                "device": engine.device, "sample_rate": 24000}

    @app.post("/v1/audio/speech", response_class=Response)
    def speech(request: SpeechRequest):
        voice = request.voice or engine.voice
        # Serve the preloaded voice; never interpret an HTTP parameter as a file
        # path or download arbitrary voices during a request.
        if voice != engine.voice:
            raise HTTPException(400, f"This service is configured for voice {engine.voice}")
        if not capacity.acquire(blocking=False):
            raise HTTPException(503, "Kokoro queue is full", headers={"Retry-After": "2"})
        try:
            audio = engine.synthesize(request.input, voice, request.speed)
            return Response(audio, media_type="audio/wav")
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        except Exception as error:
            log.exception("Kokoro synthesis failed")
            raise HTTPException(500, "Kokoro synthesis failed; check the service log") from error
        finally:
            capacity.release()

    return app


def english_voice(value: str) -> str:
    import re
    if not re.fullmatch(r"[ab][fm]_[a-z]+", value):
        raise argparse.ArgumentTypeError("Use an English Kokoro voice, e.g. af_heart or bf_emma")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8082)
    parser.add_argument("--voice", type=english_voice, default="af_heart")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--prepare", action="store_true", help="Download and warm up, then exit")
    args = parser.parse_args()
    if args.threads < 1 or not 1 <= args.port <= 65535:
        parser.error("threads must be positive and port must be between 1 and 65535")
    engine = KokoroEngine(args.voice, args.device, args.threads)
    if args.prepare:
        engine.load()
        print("Kokoro model and voice are ready.")
        return 0
    import uvicorn
    uvicorn.run(create_app(engine), host=args.host, port=args.port, workers=1,
                timeout_graceful_shutdown=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

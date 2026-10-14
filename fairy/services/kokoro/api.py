"""Kokoro health and speech endpoints with bounded inference."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import threading
from fastapi import FastAPI, HTTPException, Response
from .engine import KokoroEngine
from .schemas import SpeechRequest

log = logging.getLogger(__name__)


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

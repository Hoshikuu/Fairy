"""Persistent Kokoro model, English voice and WAV synthesis."""

from __future__ import annotations

import io
import os
import threading
from fairy.config.paths import PROJECT_ROOT as ROOT


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

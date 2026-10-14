"""Thread-safe Discord PCM buffering and silence detection."""

from __future__ import annotations

import audioop
import logging
import queue
import threading
import time
from discord.ext import voice_recv
from .buffers import SpeakerBuffer, Utterance

log = logging.getLogger(__name__)


class TranscriptionSink(voice_recv.AudioSink):
    """The receive thread only converts/buffers audio; HTTP runs asynchronously."""

    def __init__(self, *, silence_seconds=0.8, max_seconds=15, energy_threshold=150):
        super().__init__()
        self.silence_seconds = silence_seconds
        self.max_bytes = int(max_seconds * 16000 * 2)
        self.energy_threshold = energy_threshold
        self.utterances: queue.Queue[Utterance] = queue.Queue(maxsize=64)
        self.buffers: dict[int, SpeakerBuffer] = {}
        self.lock = threading.Lock()
        self.closed = False
        self.dropped = 0

    def wants_opus(self) -> bool:
        return False

    def write(self, user, data):
        if user is None or user.bot or not data.pcm:
            return
        now = time.monotonic()
        with self.lock:
            if self.closed:
                return
            buffer = self.buffers.setdefault(user.id, SpeakerBuffer())
            if buffer.pcm and now - buffer.last_voice >= self.silence_seconds:
                self._flush(user.id, buffer)
            mono = audioop.tomono(data.pcm, 2, 0.5, 0.5)
            pcm, buffer.resample_state = audioop.ratecv(
                mono, 2, 1, 48000, 16000, buffer.resample_state
            )
            voiced = audioop.rms(pcm, 2) >= self.energy_threshold
            if voiced:
                buffer.last_voice = now
                buffer.voiced_bytes += len(pcm)
            if voiced or buffer.pcm:
                buffer.pcm.extend(pcm)
            if len(buffer.pcm) >= self.max_bytes:
                self._flush(user.id, buffer)

    def _flush(self, user_id: int, buffer: SpeakerBuffer):
        # Skip pure silence and brief microphone clicks (less than 120 ms).
        if buffer.voiced_bytes >= int(0.12 * 16000 * 2):
            try:
                self.utterances.put_nowait(Utterance(user_id, bytes(buffer.pcm)))
            except queue.Full:
                self.dropped += 1
                log.warning("Whisper backlog full; dropped audio from user %s", user_id)
        buffer.pcm.clear()
        buffer.voiced_bytes = 0

    def flush_silence(self):
        now = time.monotonic()
        with self.lock:
            for user_id, buffer in list(self.buffers.items()):
                if now - buffer.last_voice >= self.silence_seconds:
                    self._flush(user_id, buffer)
                    del self.buffers[user_id]

    def cleanup(self):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            for user_id, buffer in self.buffers.items():
                self._flush(user_id, buffer)
            self.buffers.clear()

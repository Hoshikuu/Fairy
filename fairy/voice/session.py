"""Voice-session queues, worker lifecycle and bounded shutdown."""

from __future__ import annotations

import asyncio
import logging
from fairy.audio.receiver import TranscriptionSink
from . import transcription, responses, speech

log = logging.getLogger(__name__)


class VoiceTranscription:
    def __init__(self, voice_client, text_channel, whisper_lock, *, server_url, language,
                 kokoro_url="http://127.0.0.1:8082", kokoro_voice=None, kokoro_speed=1.0):
        self.voice_client = voice_client
        self.text_channel = text_channel
        self.whisper_lock = whisper_lock
        self.server_url = server_url
        self.language = language
        self.kokoro_url = kokoro_url
        self.kokoro_voice = kokoro_voice
        self.kokoro_speed = kokoro_speed
        self.stopping = False
        self.sink = TranscriptionSink()
        self.tasks: list[asyncio.Task] = []
        self.last_error = 0.0
        self.llm_queue: asyncio.Queue[tuple[int, str]] = asyncio.Queue(maxsize=32)
        self.transcription_done = asyncio.Event()
        self.llm_done = asyncio.Event()
        self.speech_queue: asyncio.Queue[tuple[int, str]] = asyncio.Queue(maxsize=8)
        self.speech_task: asyncio.Task | None = None
        self.histories: dict[int, list[dict]] = {}


    def start(self):
        loop = asyncio.get_running_loop()

        def after(error):
            if error:
                log.error("Discord voice reception stopped: %s", error)
                loop.call_soon_threadsafe(
                    lambda: loop.create_task(self._report_error(
                        "Se ha detenido la recepción de audio. Usa /join para reiniciarla."
                    ))
                )

        self.voice_client.listen(self.sink, after=after)
        self.tasks = [
            asyncio.create_task(self._flush_loop(), name="voice-silence"),
            asyncio.create_task(self._transcribe_loop(), name="voice-whisper"),
            asyncio.create_task(self._llm_loop(), name="voice-llama"),
        ]
        self.speech_task = asyncio.create_task(self._speech_loop(), name="voice-kokoro")


    async def stop(self):
        self.stopping = True
        # Cancel speech immediately, including an HTTP request or active playback.
        if self.speech_task:
            self.speech_task.cancel()
            await asyncio.gather(self.speech_task, return_exceptions=True)
            self.speech_task = None
        while not self.speech_queue.empty():
            self.speech_queue.get_nowait()
            self.speech_queue.task_done()
        self.voice_client.stop_listening()
        self.sink.cleanup()
        # Finish the last utterance, but bound shutdown if Whisper is unavailable.
        if self.tasks:
            try:
                async with asyncio.timeout(10):
                    await asyncio.gather(*self.tasks)
            except TimeoutError:
                log.warning("Stopped transcription with unfinished audio after 10 seconds")
            finally:
                for task in self.tasks:
                    task.cancel()
                await asyncio.gather(*self.tasks, return_exceptions=True)
                self.tasks.clear()

    async def _flush_loop(self):
        await transcription.flush_loop(self)

    async def _report_error(self, message):
        await transcription.report_error(self, message)

    async def _transcribe_loop(self):
        await transcription.transcribe_loop(self)

    async def _llm_loop(self):
        await responses.llm_loop(self)

    async def _speech_loop(self):
        await speech.speech_loop(self)

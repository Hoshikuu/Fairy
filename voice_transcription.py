"""Per-speaker Discord audio buffering and local Whisper transcription."""

from __future__ import annotations

import asyncio
import audioop
import logging
import queue
import threading
import time
from dataclasses import dataclass, field

import discord
from discord.ext import voice_recv

from whisper_client import transcribe_pcm
from cli import ask_req, new_history

log = logging.getLogger(__name__)


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


class VoiceTranscription:
    def __init__(self, voice_client, text_channel, whisper_lock, *, server_url, language):
        self.voice_client = voice_client
        self.text_channel = text_channel
        self.whisper_lock = whisper_lock
        self.server_url = server_url
        self.language = language
        self.sink = TranscriptionSink()
        self.tasks: list[asyncio.Task] = []
        self.last_error = 0.0
        self.llm_queue: asyncio.Queue[tuple[int, str]] = asyncio.Queue(maxsize=32)
        self.transcription_done = asyncio.Event()
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

    async def _flush_loop(self):
        while not self.sink.closed:
            self.sink.flush_silence()
            await asyncio.sleep(0.2)

    async def _report_error(self, message):
        now = time.monotonic()
        if now - self.last_error < 30:
            return
        self.last_error = now
        try:
            await self.text_channel.send(message, allowed_mentions=discord.AllowedMentions.none())
        except discord.DiscordException:
            log.exception("Could not report voice transcription error")

    async def _transcribe_loop(self):
        while True:
            try:
                utterance = self.sink.utterances.get_nowait()
            except queue.Empty:
                if self.sink.closed:
                    self.transcription_done.set()
                    return
                await asyncio.sleep(0.1)
                continue
            try:
                async with self.whisper_lock:
                    text = await transcribe_pcm(
                        utterance.pcm, server_url=self.server_url, language=self.language
                    )
                if text:
                    print(f"Voice user {utterance.user_id}: {text}")
                    for offset in range(0, len(text), 1800):
                        await self.text_channel.send(
                            f"**<@{utterance.user_id}>:** {text[offset:offset + 1800]}",
                            allowed_mentions=discord.AllowedMentions.none(),
                        )
                    try:
                        self.llm_queue.put_nowait((utterance.user_id, text))
                    except asyncio.QueueFull:
                        await self._report_error(
                            "Llama tiene demasiadas frases pendientes; esta transcripción "
                            "no se ha enviado al modelo."
                        )
            except Exception:
                log.exception("Voice transcription failed for user %s", utterance.user_id)
                await self._report_error(
                    "No he podido transcribir el audio. Comprueba que whisper-server "
                    "está disponible en el servidor configurado."
                )
            finally:
                self.sink.utterances.task_done()
            if self.sink.dropped:
                self.sink.dropped = 0
                await self._report_error(
                    "Whisper no está procesando el audio lo bastante rápido; "
                    "se han perdido fragmentos pendientes."
                )

    async def _llm_loop(self):
        while True:
            try:
                user_id, text = self.llm_queue.get_nowait()
            except asyncio.QueueEmpty:
                if self.transcription_done.is_set():
                    return
                await asyncio.sleep(0.1)
                continue
            try:
                history = self.histories.get(user_id)
                if history is None:
                    history = self.histories[user_id] = new_history()
                response = await ask_req(text, history=history)
                # Retain the system prompt and the last 20 exchanges per speaker.
                if len(history) > 41:
                    history[1:] = history[-40:]
                for offset in range(0, len(response), 1800):
                    await self.text_channel.send(
                        f"**Fairy → <@{user_id}>:** {response[offset:offset + 1800]}",
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
            except Exception:
                log.exception("Llama request failed for voice user %s", user_id)
                await self._report_error(
                    "No he podido obtener una respuesta de llama-server. "
                    "Comprueba que está disponible en http://127.0.0.1:8080."
                )
            finally:
                self.llm_queue.task_done()

    async def stop(self):
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

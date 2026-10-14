"""Audio flush, Whisper work and voice-session error reporting."""

from __future__ import annotations

import asyncio
import logging
import queue
import time
import discord
from fairy.clients.whisper import transcribe_pcm

log = logging.getLogger(__name__)


async def flush_loop(session):
    while not session.sink.closed:
        session.sink.flush_silence()
        await asyncio.sleep(0.2)


async def report_error(session, message):
    now = time.monotonic()
    if now - session.last_error < 30:
        return
    session.last_error = now
    try:
        await session.text_channel.send(message, allowed_mentions=discord.AllowedMentions.none())
    except discord.DiscordException:
        log.exception("Could not report voice transcription error")


async def transcribe_loop(session):
    while True:
        try:
            utterance = session.sink.utterances.get_nowait()
        except queue.Empty:
            if session.sink.closed:
                session.transcription_done.set()
                return
            await asyncio.sleep(0.1)
            continue
        try:
            async with session.whisper_lock:
                text = await transcribe_pcm(
                    utterance.pcm, server_url=session.server_url, language=session.language
                )
            if text:
                print(f"Voice user {utterance.user_id}: {text}")
                for offset in range(0, len(text), 1800):
                    await session.text_channel.send(
                        f"**<@{utterance.user_id}>:** {text[offset:offset + 1800]}",
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                try:
                    session.llm_queue.put_nowait((utterance.user_id, text))
                except asyncio.QueueFull:
                    await session._report_error(
                        "Llama tiene demasiadas frases pendientes; esta transcripción "
                        "no se ha enviado al modelo."
                    )
        except Exception:
            log.exception("Voice transcription failed for user %s", utterance.user_id)
            await session._report_error(
                "No he podido transcribir el audio. Comprueba que whisper-server "
                "está disponible en el servidor configurado."
            )
        finally:
            session.sink.utterances.task_done()
        if session.sink.dropped:
            session.sink.dropped = 0
            await session._report_error(
                "Whisper no está procesando el audio lo bastante rápido; "
                "se han perdido fragmentos pendientes."
            )

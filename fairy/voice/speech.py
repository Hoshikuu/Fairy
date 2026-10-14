"""Sequential Kokoro synthesis and voice playback worker."""

from __future__ import annotations

import asyncio
import logging
from fairy.clients.kokoro import synthesize_wav
from fairy.audio.playback import play_wav
from fairy.audio.text import speech_chunks

log = logging.getLogger(__name__)


async def speech_loop(session):
    while not session.stopping:
        try:
            user_id, response = session.speech_queue.get_nowait()
        except asyncio.QueueEmpty:
            if session.llm_done.is_set():
                return
            await asyncio.sleep(0.1)
            continue
        try:
            for chunk in speech_chunks(response):
                audio = await synthesize_wav(
                    chunk, server_url=session.kokoro_url, voice=session.kokoro_voice,
                    speed=session.kokoro_speed,
                )
                await play_wav(session.voice_client, audio)
        except Exception:
            log.exception("Kokoro synthesis or Discord playback failed for user %s", user_id)
            await session._report_error(
                "No he podido reproducir la respuesta. Comprueba Kokoro, "
                "el permiso Hablar y que el bot no esté silenciado en el servidor."
            )
        finally:
            session.speech_queue.task_done()

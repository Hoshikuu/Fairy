"""Generate llama replies with separate speaker histories."""

from __future__ import annotations

import asyncio
import logging
from fairy.clients.llama import ask_req, new_history

log = logging.getLogger(__name__)


async def llm_loop(session):
    while True:
        try:
            user_id, text = session.llm_queue.get_nowait()
        except asyncio.QueueEmpty:
            if session.transcription_done.is_set():
                session.llm_done.set()
                return
            await asyncio.sleep(0.1)
            continue
        try:
            history = session.histories.get(user_id)
            if history is None:
                history = session.histories[user_id] = new_history()
            response = await ask_req(text, history=history)
            # Retain the system prompt and the last 20 exchanges per speaker.
            if len(history) > 41:
                history[1:] = history[-40:]
            if response.strip() and not session.stopping:
                try:
                    session.speech_queue.put_nowait((user_id, response))
                except asyncio.QueueFull:
                    await session._report_error("Hay demasiadas respuestas de voz pendientes; "
                                             "se ha descartado esta respuesta.")
        except Exception:
            log.exception("Llama request failed for voice user %s", user_id)
            await session._report_error(
                "No he podido obtener una respuesta de llama-server. "
                "Comprueba que está disponible en http://127.0.0.1:8080."
            )
        finally:
            session.llm_queue.task_done()

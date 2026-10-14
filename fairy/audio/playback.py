"""Await Discord playback and cancel only the sender."""

from __future__ import annotations

import asyncio
from .pcm import DiscordPCM


async def play_wav(voice_client, wav: bytes):
    source = await asyncio.to_thread(DiscordPCM, wav)
    loop = asyncio.get_running_loop()
    completed = loop.create_future()

    def finish(error):
        if not completed.done():
            if error:
                completed.set_exception(error)
            else:
                completed.set_result(None)

    def after(error):
        # discord.py runs playback and its completion callback on another thread.
        try:
            loop.call_soon_threadsafe(finish, error)
        except RuntimeError:
            pass  # The event loop may close while the playback thread exits.

    try:
        voice_client.play(source, after=after)
        await asyncio.wait_for(completed, timeout=source.duration + 10)
    finally:
        if getattr(voice_client, "source", None) is source:
            # VoiceRecvClient.stop() also stops the microphone receiver.
            voice_client.stop_playing()
        source.cleanup()

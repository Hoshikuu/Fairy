import asyncio
import queue

import discord

from .pcm import FRAME_BYTES, Resampler, mono_to_stereo


class StreamingSource(discord.AudioSource):
    def __init__(self):
        self.frames = queue.Queue(maxsize=250)
        self.closed = False

    def read(self) -> bytes:
        if self.closed:
            return b""
        try:
            frame = self.frames.get(timeout=0.02)
        except queue.Empty:
            return bytes(FRAME_BYTES)
        if frame is None:
            return b""
        return frame

    def is_opus(self) -> bool:
        return False

    def cleanup(self):
        self.closed = True


class Playback:
    def __init__(self, voice_client, sample_rate: int):
        self.voice_client = voice_client
        self.source = StreamingSource()
        self.resampler = Resampler(sample_rate, 48000)
        self.pending = bytearray()
        self.done = asyncio.get_running_loop().create_future()
        self.started = False

    def start(self):
        if self.started or self.source.closed:
            return
        loop = asyncio.get_running_loop()

        def complete(error):
            def finish():
                if not self.done.done():
                    if error:
                        self.done.set_exception(error)
                    else:
                        self.done.set_result(None)
            try:
                loop.call_soon_threadsafe(finish)
            except RuntimeError:
                pass

        self.voice_client.play(self.source, after=complete)
        self.started = True

    async def _put(self, frame):
        while not self.source.closed:
            try:
                self.source.frames.put_nowait(frame)
                return
            except queue.Full:
                await asyncio.sleep(0.01)
        return

    async def write(self, pcm: bytes):
        if not pcm or self.source.closed:
            return
        self.pending.extend(mono_to_stereo(self.resampler.convert(pcm)))
        while len(self.pending) >= FRAME_BYTES:
            frame = bytes(self.pending[:FRAME_BYTES])
            del self.pending[:FRAME_BYTES]
            await self._put(frame)
            if self.source.closed:
                return
            if not self.started:
                self.start()

    async def finish(self):
        if self.source.closed:
            return
        self.pending.extend(mono_to_stereo(self.resampler.convert(b"", final=True)))
        if self.pending:
            await self._put(bytes(self.pending).ljust(FRAME_BYTES, b"\0"))
            self.pending.clear()
            if self.source.closed:
                return
            if not self.started:
                self.start()
        if self.started:
            await self._put(None)
            await asyncio.wait_for(asyncio.shield(self.done), timeout=30)

    def stop(self):
        if self.started and getattr(self.voice_client, "source", None) is self.source:
            self.voice_client.stop_playing()
        self.source.cleanup()

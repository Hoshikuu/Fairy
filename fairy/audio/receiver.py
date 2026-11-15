import asyncio

from discord.ext import voice_recv


class Receiver(voice_recv.AudioSink):
    def __init__(self, loop, frames: asyncio.Queue):
        super().__init__()
        self.loop = loop
        self.frames = frames
        self.closed = False
        self.dropped = 0

    def wants_opus(self):
        return False

    def write(self, user, data):
        if self.closed or user is None or user.bot or not data.pcm:
            return
        item = (user.id, bytes(data.pcm))

        def enqueue():
            if self.closed:
                return
            try:
                self.frames.put_nowait(item)
            except asyncio.QueueFull:
                self.dropped += 1

        try:
            self.loop.call_soon_threadsafe(enqueue)
        except RuntimeError:
            pass

    def cleanup(self):
        self.closed = True

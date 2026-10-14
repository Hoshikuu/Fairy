"""Local voice/text test transports using the real Opus encoder."""

from __future__ import annotations

import threading
import discord


class LocalVoice:
    """Consume Discord audio frames using the actual Opus encoder."""

    def __init__(self):
        self.source = None
        self.packets = 0
        self.encoder = discord.opus.Encoder()
        self.players = []

    def listen(self, sink, *, after):
        pass

    def stop_listening(self):
        pass

    def play(self, source, *, after):
        self.source = source
        stop = threading.Event()
        self.current_stop = stop

        def consume():
            try:
                while not stop.is_set():
                    frame = source.read()
                    if not frame:
                        break
                    packet = self.encoder.encode(frame, 960)
                    if not packet:
                        raise RuntimeError("Opus produced no packet")
                    self.packets += 1
            except Exception as error:
                after(error)
            else:
                after(None)

        player = threading.Thread(target=consume)
        self.players.append(player)
        player.start()

    def stop_playing(self):
        self.current_stop.set()
        self.source = None


class LocalText:
    def __init__(self):
        self.messages = []

    async def send(self, message, **kwargs):
        self.messages.append(message)
        print(message, flush=True)

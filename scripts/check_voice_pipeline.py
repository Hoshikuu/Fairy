"""Check the real local STT/LLM/TTS pipeline without connecting to Discord.

Run with a Python environment containing the bot dependencies. The supervisor
uses .venv-kokoro for TTS. All processes started here are stopped on exit.
"""

import argparse
import asyncio
from collections import deque
from pathlib import Path
import socket
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import discord
from openai import AsyncOpenAI

import cli
from kokoro_client import DiscordPCM, synthesize_wav
from voice_transcription import VoiceTranscription


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


async def exercise(ports):
    kokoro_url = f"http://127.0.0.1:{ports[2]}"
    input_wav = await synthesize_wav("Hello Fairy. Please say hello in one short sentence.", server_url=kokoro_url)
    voice, text = LocalVoice(), LocalText()
    session = VoiceTranscription(voice, text, asyncio.Lock(),
        server_url=f"http://127.0.0.1:{ports[1]}", language="en", kokoro_url=kokoro_url)
    old_client = cli.client
    async with AsyncOpenAI(base_url=f"http://127.0.0.1:{ports[0]}/v1", api_key="no-key",
                           timeout=90, max_retries=0) as client:
        cli.client = client
        try:
            session.start()
            source = DiscordPCM(input_wav)
            user = type("User", (), {"id": 123, "bot": False})()
            while frame := source.read():
                data = type("Frame", (), {"pcm": frame})()
                session.sink.write(user, data)
            source.cleanup()
            session.sink.cleanup()
            async with asyncio.timeout(180):
                await asyncio.gather(*session.tasks, session.speech_task)
            if not session.histories.get(123) or voice.packets < 1:
                raise RuntimeError("The voice response did not reach Opus encoding")
            if len(text.messages) != 1:
                raise RuntimeError("Unexpected error or text answer: " + repr(text.messages))
            print(f"Real Whisper -> llama -> Kokoro -> PCM -> Opus: {voice.packets} packets", flush=True)
        finally:
            await session.stop()
            cli.client = old_client
            for player in voice.players:
                player.join(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--startup-timeout", type=float, default=240)
    args = parser.parse_args()
    ports = []
    for _ in range(3):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            ports.append(sock.getsockname()[1])
    if len(set(ports)) != 3:
        raise RuntimeError("Duplicate temporary ports; rerun the check")
    command = [sys.executable, "-u", str(ROOT / "llama_start.py"),
               "--llama-port", str(ports[0]), "--whisper-port", str(ports[1]),
               "--kokoro-port", str(ports[2])]
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    ready = threading.Event()
    lines = deque(maxlen=150)

    def drain():
        for line in process.stdout:
            lines.append(line)
            if "ready:" in line:
                print(line.strip(), flush=True)
            if "All three services are ready" in line:
                ready.set()
        ready.set()

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    try:
        if not ready.wait(args.startup_timeout) or process.poll() is not None:
            raise RuntimeError("Supervisor failed:\n" + "".join(lines))
        asyncio.run(exercise(ports))
    finally:
        if process.poll() is None:
            process.stdin.write("q\n")
            process.stdin.flush()
            process.wait(timeout=40)
        reader.join(timeout=5)
        print(f"Supervisor stopped (exit {process.returncode})", flush=True)


if __name__ == "__main__":
    main()

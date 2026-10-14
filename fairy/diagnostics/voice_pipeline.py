"""Check the real local STT/LLM/TTS pipeline without connecting to Discord.

Run with a Python environment containing the bot dependencies. The supervisor
uses .venv-kokoro for TTS. All processes started here are stopped on exit.
"""

import argparse
import os
import asyncio
from collections import deque
from pathlib import Path
import socket
import subprocess
import sys
import threading
import tempfile
import uuid

from fairy.config.paths import PROJECT_ROOT as ROOT, KOKORO_PYTHON

from openai import AsyncOpenAI

from fairy.clients import llama as cli
from fairy.audio.pcm import DiscordPCM
from fairy.clients.kokoro import synthesize_wav
from fairy.voice.session import VoiceTranscription
from .transports import LocalVoice, LocalText
from fairy.runtime.launcher import wait_for_services
from fairy.runtime.shutdown import stop_process


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
    with tempfile.TemporaryDirectory(prefix="fairy-diagnostic-") as directory:
        ready_file = Path(directory) / "ready.json"
        ready_token = uuid.uuid4().hex
        command = [str(KOKORO_PYTHON), "-u", "-m", "fairy.start",
                   "--llama-port", str(ports[0]), "--whisper-port", str(ports[1]),
                   "--kokoro-port", str(ports[2]), "--ready-file", str(ready_file), "--ready-token", ready_token]
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            start_new_session=os.name != "nt")
        lines = deque(maxlen=150)

        def drain():
            for line in process.stdout:
                lines.append(line)
                if "ready:" in line:
                    print(line.strip(), flush=True)

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        try:
            wait_for_services(process, ready_file, args.startup_timeout, threading.Event(), ready_token=ready_token)
            asyncio.run(exercise(ports))
        except Exception:
            print("".join(lines), file=sys.stderr)
            raise
        finally:
            stop_process(process, stdin_quit=True, timeout=30)
            reader.join(timeout=5)
            print(f"Supervisor stopped (exit {process.returncode})", flush=True)


if __name__ == "__main__":
    main()

"""Private newline-delimited protocol between Electron and the local models."""

import asyncio
import base64
import json
import os
import sys
import threading
import time

from fairy.desktop.session import DesktopSession
from fairy.desktop.control import desktop_tools
from fairy.desktop.job import attach_process_job
from fairy.paths import PROMPT, ROOT
from fairy.realtime.omni import OmniClient
from fairy.runner.dual import brain_settings, omni_settings, start_brain, start_omni
from fairy.runner.main import stop_llama

MAX_LINE = 5 * 1024 * 1024


class Bridge:
    def __init__(self, output) -> None:
        self.output = output
        self.frame = None
        self.frame_time = 0.0
        self.session = None
        self.turn = None
        self.startup = None
        self.stopping = asyncio.Event()
        self.brain_process = None
        self.omni_process = None
        self.control_enabled = False

    def emit(self, kind: str, **data) -> None:
        self.output.write(json.dumps({"type": kind, **data}, ensure_ascii=True) + "\n")
        self.output.flush()

    def current_frame(self):
        return self.frame if time.monotonic() - self.frame_time < 8 else None

    async def start(self) -> None:
        try:
            port = int(os.getenv("FAIRY_DESKTOP_OMNI_PORT", "8080"))
            if omni_settings(port)[0] != port or brain_settings()[0] == port:
                raise ValueError("Model ports must be different and match their configured URLs")
            self.emit("status", message="Starting MiniCPM…")
            self.brain_process = await start_brain(360)
            self.emit("status", message="Starting LFM3…")
            self.omni_process = await start_omni(360, port)
            omni = OmniClient(f"http://127.0.0.1:{port}",
                              asr_language=os.getenv("FAIRY_ASR_LANGUAGE", "English"),
                              tts_language=os.getenv("FAIRY_TTS_LANGUAGE", "English"),
                              voice=os.getenv("FAIRY_TTS_VOICE", "female"))
            self.session = DesktopSession(omni, PROMPT.read_text(encoding="utf-8"))
            self.session.brain.tools.update(desktop_tools(lambda: self.control_enabled,
                                                         lambda action: self.emit("action", message=action)))
            self.emit("ready", pid=os.getpid())
            while not self.stopping.is_set():
                if self.brain_process.poll() is not None or self.omni_process.poll() is not None:
                    raise RuntimeError("A model server stopped unexpectedly")
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self.emit("fatal", message=str(error))
            self.stopping.set()

    async def answer(self, message: dict) -> None:
        try:
            if self.session is None:
                raise ValueError("Models are not ready")
            text = message.get("text")
            pcm = None
            if "audio" in message:
                pcm = base64.b64decode(message["audio"], validate=True)
                if not pcm or len(pcm) > 1920000 or len(pcm) % 2:
                    raise ValueError("Invalid or oversized microphone audio")
            elif not isinstance(text, str) or not 0 < len(text.strip()) <= 4000:
                raise ValueError("Invalid message")

            async def audio(chunk: bytes) -> None:
                self.emit("audio", data=base64.b64encode(chunk).decode("ascii"))

            result = await self.session.respond(text=text if pcm is None else None, pcm=pcm,
                                                on_audio=audio, frame_provider=self.current_frame)
            self.emit("answer", text=result)
        except asyncio.CancelledError:
            self.emit("cancelled")
            raise
        except Exception as error:
            self.emit("error", message=str(error))
        finally:
            self.turn = None

    async def command(self, message: dict) -> None:
        kind = message.get("type")
        if kind == "shutdown":
            self.stopping.set()
        elif kind == "cancel":
            if self.turn:
                self.turn.cancel()
                await asyncio.gather(self.turn, return_exceptions=True)
        elif kind == "frame":
            encoded = message.get("data", "")
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) > 1024 * 1024 or not raw.startswith(b"\xff\xd8\xff") or not raw.endswith(b"\xff\xd9"):
                raise ValueError("Invalid screen frame")
            self.frame, self.frame_time = encoded, time.monotonic()
        elif kind == "clear_frame":
            self.frame = None
        elif kind == "control":
            self.control_enabled = message.get("enabled") is True
        elif kind == "reset":
            if self.turn:
                raise ValueError("Stop the current turn first")
            if self.session:
                self.session.brain.history.clear()
        elif kind == "turn":
            if self.turn:
                raise ValueError("A turn is already running")
            self.turn = asyncio.create_task(self.answer(message))
        else:
            raise ValueError("Unknown command")

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue(maxsize=8)

        def read_input() -> None:
            while True:
                line = sys.stdin.buffer.readline(MAX_LINE + 1)
                if not line or len(line) > MAX_LINE:
                    loop.call_soon_threadsafe(self.stopping.set)
                    return
                future = asyncio.run_coroutine_threadsafe(queue.put(line), loop)
                try:
                    future.result()
                except Exception:
                    return
                try:
                    if json.loads(line).get("type") == "shutdown":
                        return
                except (ValueError, AttributeError):
                    pass

        reader = threading.Thread(target=read_input, daemon=True)
        reader.start()
        self.startup = asyncio.create_task(self.start())
        try:
            while not self.stopping.is_set():
                try:
                    line = await asyncio.wait_for(queue.get(), 0.2)
                except TimeoutError:
                    continue
                try:
                    message = json.loads(line)
                    if not isinstance(message, dict):
                        raise ValueError("Expected a command object")
                    await self.command(message)
                except (ValueError, TypeError) as error:
                    self.emit("error", message=str(error))
        finally:
            if self.turn:
                self.turn.cancel()
                await asyncio.gather(self.turn, return_exceptions=True)
            if self.session:
                await self.session.close()
            self.startup.cancel()
            await asyncio.gather(self.startup, return_exceptions=True)
            await stop_llama(self.omni_process)
            await stop_llama(self.brain_process)
            await asyncio.to_thread(reader.join, 2)


def main() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    protocol = sys.stdout
    sys.stdout = sys.stderr
    # The kernel closes this handle on exit, including an abrupt bridge failure.
    job = attach_process_job()
    asyncio.run(Bridge(protocol).run())


if __name__ == "__main__":
    main()

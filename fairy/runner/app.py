import argparse
import asyncio
import subprocess
import sys
import threading

from fairy.bot.main import FairyBot, get_token
from fairy.paths import DRAFT_MODEL, PROMPT, SERVER
from pathlib import Path
import os
from fairy.runner.main import check_port, stop_llama
from fairy.runner.dual import brain_settings, omni_settings, start_brain, start_omni
from aiohttp import web
from fairy.web.server import create_app


def read_quit(loop: asyncio.AbstractEventLoop, stop: asyncio.Event) -> None:
    for line in sys.stdin:
        if line.strip().lower() == "q":
            loop.call_soon_threadsafe(stop.set)
            return


async def run(port: int, timeout: float, web_port: int = 8081) -> None:
    token = get_token()
    process = None
    brain_process = None
    bot = None
    bot_task = None
    web_runner = None
    startup_tasks = []
    quit_tasks = []
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    threading.Thread(target=read_quit, args=(loop, stop), daemon=True).start()
    try:
        omni_port, _, _, _, _ = omni_settings(port)
        if omni_port != port:
            raise RuntimeError("FAIRY_OMNI_URL port must match --port")
        brain_port, _, _, _ = brain_settings()
        if len({brain_port, port, web_port}) != 3:
            raise RuntimeError("MiniCPM, LFM3 and web require separate ports")
        brain_task = asyncio.create_task(start_brain(timeout))
        startup_tasks.append(brain_task)
        quit_task = asyncio.create_task(stop.wait())
        quit_tasks.append(quit_task)
        done, _ = await asyncio.wait((brain_task, quit_task), return_when=asyncio.FIRST_COMPLETED)
        if quit_task in done:
            if brain_task.done() and not brain_task.cancelled() and brain_task.exception() is None:
                brain_process = brain_task.result()
            else:
                brain_task.cancel()
                await asyncio.gather(brain_task, return_exceptions=True)
            return
        quit_task.cancel()
        await asyncio.gather(quit_task, return_exceptions=True)
        brain_process = await brain_task
        omni_task = asyncio.create_task(start_omni(timeout, port))
        startup_tasks.append(omni_task)
        quit_task = asyncio.create_task(stop.wait())
        quit_tasks.append(quit_task)
        done, _ = await asyncio.wait((omni_task, quit_task), return_when=asyncio.FIRST_COMPLETED)
        if quit_task in done:
            if omni_task.done() and not omni_task.cancelled() and omni_task.exception() is None:
                process = omni_task.result()
            else:
                omni_task.cancel()
                await asyncio.gather(omni_task, return_exceptions=True)
            return
        quit_task.cancel()
        await asyncio.gather(quit_task, return_exceptions=True)
        process = await omni_task
        bot = FairyBot(port)
        web_runner = web.AppRunner(create_app())
        await web_runner.setup()
        await web.TCPSite(web_runner, "127.0.0.1", web_port).start()
        print(f"[PASS]  Fairy web: http://127.0.0.1:{web_port}", flush=True)
        print(f"[INFO]  Model API: http://127.0.0.1:{port}", flush=True)
        bot_task = asyncio.create_task(bot.start(token))
        print("[INFO]  Press q + Enter or Ctrl+C to stop Fairy", flush=True)
        while not stop.is_set():
            if process.poll() is not None:
                raise RuntimeError(f"llama-server exited with code {process.returncode}")
            if brain_process.poll() is not None:
                raise RuntimeError(f"MiniCPM server exited with code {brain_process.returncode}")
            if bot_task.done():
                await bot_task
                raise RuntimeError("Discord bot stopped unexpectedly")
            try:
                await asyncio.wait_for(stop.wait(), timeout=0.2)
            except TimeoutError:
                pass
    finally:
        for task in quit_tasks:
            task.cancel()
        await asyncio.gather(*quit_tasks, return_exceptions=True)
        for task in startup_tasks:
            if not task.done():
                task.cancel()
        started = await asyncio.gather(*startup_tasks, return_exceptions=True)
        if bot_task is not None:
            bot_task.cancel()
            await asyncio.gather(bot_task, return_exceptions=True)
        if web_runner is not None:
            await web_runner.cleanup()
        if bot is not None:
            await bot.close()
        owned = [process, brain_process]
        owned.extend(result for result in started if not isinstance(result, BaseException))
        seen = set()
        for child in owned:
            if child is not None and id(child) not in seen:
                seen.add(id(child))
                await stop_llama(child)


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Fairy's local model and Discord bot")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--web-port", type=int, default=8081)
    parser.add_argument("--startup-timeout", type=float, default=360)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not 1 <= args.web_port <= 65535 or args.port == args.web_port or not 0 < args.startup_timeout < float("inf"):
        parser.error("Invalid port or startup timeout")
    try:
        if args.check:
            from fairy.installation.installer import check_environment, check_llama
            import discord

            get_token()
            check_environment()
            check_llama()
            check_port(args.port)
            check_port(args.web_port)
            brain_port, brain_model, _, _ = brain_settings()
            if len({brain_port, args.port, args.web_port}) != 3:
                raise RuntimeError("MiniCPM, LFM3 and web require separate ports")
            check_port(brain_port)
            omni_port, model, projector, _, _ = omni_settings(args.port)
            if omni_port != args.port:
                raise RuntimeError("FAIRY_OMNI_URL port must match --port")
            draft = Path(os.getenv("FAIRY_DRAFT_MODEL_PATH", str(DRAFT_MODEL)))
            for path in (model, projector, brain_model, draft):
                if not path.is_file():
                    raise RuntimeError(f"Missing LFM3 component: {path}")
            discord.opus.Encoder()
            paths = (SERVER, PROMPT)
            for path in paths:
                if not path.is_file():
                    raise RuntimeError(f"Missing file: {path}")
            print("[PASS]  Configuration, dependencies, Opus, model files and port ready; no login")
            return 0
        asyncio.run(run(args.port, args.startup_timeout, args.web_port))
        return 0
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError, TimeoutError, ValueError, subprocess.SubprocessError) as error:
        print(f"[ERROR]  {error}", file=sys.stderr)
        return 1

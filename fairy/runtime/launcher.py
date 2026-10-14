"""Start fairy.start, wait for owned services, then start fairy.bot."""
from pathlib import Path
import json
import math
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from fairy.config.paths import PROJECT_ROOT, BOT_PYTHON
from fairy.services.supervisor.arguments import build_parser
from fairy.services.supervisor.processes import log_output, listen_for_quit
from fairy.services.supervisor.validation import validate_services
from .environment import require_dependencies, run_python
from .shutdown import install_stop_handlers, restore_handlers, stop_process


def parse_args(argv=None):
    parser = build_parser()
    parser.description = __doc__
    parser.add_argument("--bot-python", type=Path, default=BOT_PYTHON)
    parser.add_argument("--startup-timeout", type=float, default=360)
    args = parser.parse_args(argv)
    if not math.isfinite(args.startup_timeout) or args.startup_timeout <= 0:
        parser.error("startup-timeout must be positive")
    return args


def start_child(name, python, module, arguments, *, stdin=False, env=None):
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen([str(python), "-u", "-m", module, *arguments],
        cwd=PROJECT_ROOT, stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", bufsize=1, creationflags=flags,
        start_new_session=os.name != "nt", env=env)
    threading.Thread(target=log_output, args=(name, process), daemon=True).start()
    return process


def service_arguments(args, ready_file, ready_token):
    return ["--host", args.host, "--llama-port", str(args.llama_port),
            "--whisper-port", str(args.whisper_port), "--kokoro-port", str(args.kokoro_port),
            "--llama-model", str(args.llama_model.resolve()),
            "--whisper-model", str(args.whisper_model.resolve()),
            "--llama-gpu-layers", str(args.llama_gpu_layers),
            "--kokoro-python", str(args.kokoro_python.resolve()),
            "--kokoro-voice", args.kokoro_voice, "--kokoro-device", args.kokoro_device,
            "--kokoro-threads", str(args.kokoro_threads), "--ready-file", str(ready_file),
            "--ready-token", ready_token]


def wait_for_services(process, ready_file, timeout, stop_event, *, ready_token=None):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stop_event.is_set():
            return False
        if process.poll() is not None:
            raise RuntimeError(f"Service supervisor exited with code {process.returncode}")
        if ready_file.is_file():
            ready = json.loads(ready_file.read_text(encoding="utf-8"))
            owned = ready.get("token") == ready_token if ready_token is not None else ready.get("pid") == process.pid
            # Windows venv redirectors have a different PID from the interpreter.
            if ready.get("status") == "ready" and owned:
                return True
        time.sleep(0.1)
    raise RuntimeError(f"Services were not ready within {timeout:.0f} seconds")


def bot_environment(args):
    host = "127.0.0.1" if args.host == "0.0.0.0" else args.host
    env = os.environ.copy()
    env.update(LLAMA_URL=f"http://{host}:{args.llama_port}/v1",
               WHISPER_URL=f"http://{host}:{args.whisper_port}",
               KOKORO_URL=f"http://{host}:{args.kokoro_port}", KOKORO_VOICE=args.kokoro_voice)
    return env


def main(argv=None):
    args = parse_args(argv)
    services = bot = None
    stop_event = threading.Event()
    handlers = install_stop_handlers(stop_event)
    try:
        require_dependencies(args.bot_python, "bot")
        run_python(args.bot_python, ["-m", "fairy.bot", "--check"], capture=True, timeout=60)
        validate_services(args)
        if args.check:
            print("Bot, services, configuration and ports are ready.")
            return 0
        threading.Thread(target=listen_for_quit, args=(stop_event,), daemon=True).start()
        with tempfile.TemporaryDirectory(prefix="fairy-ready-") as directory:
            ready_file = Path(directory) / "services.json"
            ready_token = uuid.uuid4().hex
            services = start_child("SERVICES", args.kokoro_python, "fairy.start",
                                   service_arguments(args, ready_file, ready_token), stdin=True)
            if not wait_for_services(services, ready_file, args.startup_timeout, stop_event, ready_token=ready_token):
                return 0
            bot = start_child("BOT", args.bot_python, "fairy.bot", [], stdin=True, env=bot_environment(args))
            print("Fairy started. Ctrl+C or q + Enter stops the bot and services.", flush=True)
            while not stop_event.is_set():
                for name, process in (("services", services), ("bot", bot)):
                    if process.poll() is not None:
                        raise RuntimeError(f"{name} exited with code {process.returncode}")
                time.sleep(0.2)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        detail = ((getattr(error, "stderr", None) or "")[-2000:])
        print(f"Startup error: {error}\n{detail}", file=sys.stderr)
        return 1
    finally:
        # Close Discord before its local backends; every child has a bounded wait.
        try:
            stop_process(bot, stdin_quit=True, timeout=20)
        finally:
            try:
                stop_process(services, stdin_quit=True, timeout=30)
            finally:
                restore_handlers(handlers)

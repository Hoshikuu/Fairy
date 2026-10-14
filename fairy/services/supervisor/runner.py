"""Supervise Whisper, llama and Kokoro together."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from fairy.config.paths import PROJECT_ROOT, LLAMA_SERVER, WHISPER_SERVER
from .arguments import parse_args
from .commands import build_commands
from .validation import validate_services
from .processes import launch, wait_ready, stop_children, listen_for_quit
from fairy.runtime.shutdown import install_stop_handlers, restore_handlers


def main(argv=None) -> int:
    args = parse_args(argv)
    children: dict[str, subprocess.Popen[str]] = {}
    stop_event = threading.Event()
    handlers = install_stop_handlers(stop_event)
    try:
        threading.Thread(target=listen_for_quit, args=(stop_event,), daemon=True).start()
        validate_services(args)

        if args.check:
            print("Files and ports are ready.")
            print(f"llama.cpp:   {args.llama_model} -> {args.host}:{args.llama_port}")
            print(f"whisper.cpp: {args.whisper_model} -> {args.host}:{args.whisper_port}")
            print(f"Kokoro:      {args.kokoro_voice} ({args.kokoro_device}) -> {args.host}:{args.kokoro_port}")
            return 0

        whisper_command, llama_command, kokoro_command = build_commands(args)

        launch("WHISPER", whisper_command, children)
        wait_ready("WHISPER", args.host, args.whisper_port, children, timeout=90, stop_event=stop_event)
        launch("LLAMA", llama_command, children)
        wait_ready("LLAMA", args.host, args.llama_port, children, timeout=180, stop_event=stop_event)
        launch("KOKORO", kokoro_command, children)
        wait_ready("KOKORO", args.host, args.kokoro_port, children, timeout=180, stop_event=stop_event)

        if args.ready_file is not None:
            temporary = args.ready_file.with_suffix(".tmp")
            temporary.write_text(json.dumps({"status": "ready", "pid": os.getpid(),
                                              "token": args.ready_token}), encoding="utf-8")
            temporary.replace(args.ready_file)

        print("\nAll three services are ready. Press Ctrl+C or type q + Enter to stop them.")
        display_host = "127.0.0.1" if args.host == "0.0.0.0" else args.host
        print(f"LLM:     http://{display_host}:{args.llama_port}/v1")
        print(f"Whisper: http://{display_host}:{args.whisper_port}/inference")
        print(f"Kokoro:  http://{display_host}:{args.kokoro_port}/v1/audio/speech")
        if args.host == "0.0.0.0":
            print("LAN clients can use this computer's IP address instead of 127.0.0.1.")
        while not stop_event.is_set():
            for name, process in children.items():
                if process.poll() is not None:
                    raise RuntimeError(f"{name} exited with code {process.returncode}")
            time.sleep(0.5)
        print("\nStopping services...")
        return 0
    except (KeyboardInterrupt, InterruptedError):
        print("\nStopping services...")
        return 0
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"\nStartup or service error: {error}", file=sys.stderr)
        return 1
    finally:
        try:
            stop_children(children)
        finally:
            restore_handlers(handlers)

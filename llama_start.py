"""Start Fairy's llama.cpp, whisper.cpp and Kokoro HTTP services together.

Run ``python llama_start.py`` for local clients, or add ``--host 0.0.0.0``
to listen on the LAN. Press Ctrl+C to stop all child processes.
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
LLAMA_SERVER = PROJECT_ROOT / "llama" / "llama-server.exe"
WHISPER_SERVER = PROJECT_ROOT / "whisper" / "Release" / "whisper-server.exe"
LLAMA_MODEL = PROJECT_ROOT / "models" / "Spark-X2.5-4B-Q4_K_M.gguf"
WHISPER_MODEL = PROJECT_ROOT / "models" / "ggml-small.bin"
KOKORO_PYTHON = PROJECT_ROOT / ".venv-kokoro" / (
    "Scripts/python.exe" if os.name == "nt" else "bin/python"
)
KOKORO_SERVER = PROJECT_ROOT / "kokoro_server.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Bind address for all servers")
    parser.add_argument("--llama-port", type=int, default=8080)
    parser.add_argument("--whisper-port", type=int, default=8081)
    parser.add_argument("--kokoro-port", type=int, default=8082)
    parser.add_argument("--kokoro-python", type=Path, default=KOKORO_PYTHON)
    parser.add_argument("--kokoro-voice", default="af_heart")
    parser.add_argument("--kokoro-device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--kokoro-threads", type=int, default=4)
    parser.add_argument("--llama-model", type=Path, default=LLAMA_MODEL)
    parser.add_argument("--whisper-model", type=Path, default=WHISPER_MODEL)
    parser.add_argument("--llama-gpu-layers", type=int, default=99)
    parser.add_argument("--check", action="store_true", help="Check files and ports, then exit")
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{label} not found or empty: {path}")


def require_port(host: str, port: int) -> None:
    if not 1 <= port <= 65535:
        raise RuntimeError(f"Invalid port: {port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, port))
    except OSError as error:
        raise RuntimeError(f"Cannot use {host}:{port}: {error}") from error


def log_output(name: str, process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[{name}] {line}", end="", flush=True)


def launch(name: str, command: list[str], children: dict[str, subprocess.Popen[str]]) -> None:
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=flags,
    )
    children[name] = process
    threading.Thread(target=log_output, args=(name, process), daemon=True).start()
    print(f"{name} started (PID {process.pid})", flush=True)


def wait_ready(
    name: str,
    host: str,
    port: int,
    children: dict[str, subprocess.Popen[str]],
    timeout: float,
) -> None:
    probe_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{probe_host}:{port}/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for child_name, process in children.items():
            if process.poll() is not None:
                raise RuntimeError(f"{child_name} exited with code {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    print(f"{name} ready: {url}", flush=True)
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{name} did not become ready within {timeout:.0f} seconds")


def stop_children(children: dict[str, subprocess.Popen[str]]) -> None:
    active = [process for process in children.values() if process.poll() is None]
    for process in active:
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.terminate()
        except OSError:
            process.terminate()

    for process in active:
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def listen_for_quit(stop_event: threading.Event) -> None:
    if sys.stdin is None:
        return
    while not stop_event.is_set():
        line = sys.stdin.readline()
        if not line:
            return
        if line.strip().lower() == "q":
            stop_event.set()
            return


def main() -> int:
    args = parse_args()
    children: dict[str, subprocess.Popen[str]] = {}
    stop_event = threading.Event()
    try:
        if len({args.llama_port, args.whisper_port, args.kokoro_port}) != 3:
            raise RuntimeError("llama.cpp, whisper.cpp and Kokoro need different ports")
        if args.kokoro_threads < 1 or not re.fullmatch(r"[ab][fm]_[a-z]+", args.kokoro_voice):
            raise RuntimeError("Kokoro requires positive threads and an English voice such as af_heart")
        require_file(LLAMA_SERVER, "llama-server")
        require_file(WHISPER_SERVER, "whisper-server")
        require_file(args.llama_model, "LLM model")
        require_file(args.whisper_model, "Whisper GGML model")
        require_file(args.kokoro_python, "Kokoro Python (run python setup/kokoro_setup.py)")
        require_file(KOKORO_SERVER, "Kokoro service script")
        result = subprocess.run(
            [str(args.kokoro_python), "-c", "import kokoro, fastapi, uvicorn, soundfile; import en_core_web_sm"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=60,
        )
        if result.returncode:
            raise RuntimeError("Kokoro dependencies unavailable. Run python setup/kokoro_setup.py.\n"
                               + result.stderr[-2000:])
        require_port(args.host, args.llama_port)
        require_port(args.host, args.whisper_port)
        require_port(args.host, args.kokoro_port)

        if args.check:
            print("Files and ports are ready.")
            print(f"llama.cpp:   {args.llama_model} -> {args.host}:{args.llama_port}")
            print(f"whisper.cpp: {args.whisper_model} -> {args.host}:{args.whisper_port}")
            print(f"Kokoro:      {args.kokoro_voice} ({args.kokoro_device}) -> {args.host}:{args.kokoro_port}")
            return 0

        whisper_command = [
            str(WHISPER_SERVER),
            "--model", str(args.whisper_model.resolve()),
            "--host", args.host,
            "--port", str(args.whisper_port),
            "--language", "en",
            "--no-gpu",
            "--threads", "4",
        ]
        llama_command = [
            str(LLAMA_SERVER),
            "--model", str(args.llama_model.resolve()),
            "--alias", "Hoshiku/HadaAI",
            "--host", args.host,
            "--port", str(args.llama_port),
            "--ctx-size", "16384",
            "--predict", "1024",
            "--threads", "8",
            "--gpu-layers", str(args.llama_gpu_layers),
            "--batch-size", "2048",
            "--ubatch-size", "512",
            "--flash-attn", "on",
            "--cache-type-k", "q8_0",
            "--cache-type-v", "q8_0",
            "--jinja",
            "--no-webui",
        ]

        launch("WHISPER", whisper_command, children)
        wait_ready("WHISPER", args.host, args.whisper_port, children, timeout=90)
        launch("LLAMA", llama_command, children)
        wait_ready("LLAMA", args.host, args.llama_port, children, timeout=180)
        launch("KOKORO", [str(args.kokoro_python), "-u", str(KOKORO_SERVER),
                          "--host", args.host, "--port", str(args.kokoro_port),
                          "--voice", args.kokoro_voice, "--device", args.kokoro_device,
                          "--threads", str(args.kokoro_threads)], children)
        wait_ready("KOKORO", args.host, args.kokoro_port, children, timeout=180)

        print("\nAll three services are ready. Press Ctrl+C or type q + Enter to stop them.")
        display_host = "127.0.0.1" if args.host == "0.0.0.0" else args.host
        print(f"LLM:     http://{display_host}:{args.llama_port}/v1")
        print(f"Whisper: http://{display_host}:{args.whisper_port}/inference")
        print(f"Kokoro:  http://{display_host}:{args.kokoro_port}/v1/audio/speech")
        if args.host == "0.0.0.0":
            print("LAN clients can use this computer's IP address instead of 127.0.0.1.")
        threading.Thread(target=listen_for_quit, args=(stop_event,), daemon=True).start()
        while not stop_event.is_set():
            for name, process in children.items():
                if process.poll() is not None:
                    raise RuntimeError(f"{name} exited with code {process.returncode}")
            time.sleep(0.5)
        print("\nStopping services...")
        return 0
    except KeyboardInterrupt:
        print("\nStopping services...")
        return 0
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"\nStartup or service error: {error}", file=sys.stderr)
        return 1
    finally:
        stop_children(children)


if __name__ == "__main__":
    raise SystemExit(main())

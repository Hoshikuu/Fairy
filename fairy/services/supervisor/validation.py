"""Check local files, dependencies and port availability."""

from __future__ import annotations

import socket
from pathlib import Path
import re
from fairy.config.paths import LLAMA_SERVER, WHISPER_SERVER
from fairy.runtime.environment import require_dependencies


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


def validate_services(args, *, ports=True):
    if len({args.llama_port, args.whisper_port, args.kokoro_port}) != 3:
        raise RuntimeError("llama.cpp, whisper.cpp and Kokoro need different ports")
    if args.kokoro_threads < 1 or not re.fullmatch(r"[ab][fm]_[a-z]+", args.kokoro_voice):
        raise RuntimeError("Kokoro requires positive threads and an English voice such as af_heart")
    for path, label in ((LLAMA_SERVER, "llama-server"), (WHISPER_SERVER, "whisper-server"),
                        (args.llama_model, "LLM model"), (args.whisper_model, "Whisper model")):
        require_file(path, label)
    require_dependencies(args.kokoro_python, "kokoro")
    if ports:
        for port in (args.llama_port, args.whisper_port, args.kokoro_port):
            require_port(args.host, port)

"""Kokoro command-line options and server startup."""

from __future__ import annotations

import argparse
from .engine import KokoroEngine
from .api import create_app


def english_voice(value: str) -> str:
    import re
    if not re.fullmatch(r"[ab][fm]_[a-z]+", value):
        raise argparse.ArgumentTypeError("Use an English Kokoro voice, e.g. af_heart or bf_emma")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8082)
    parser.add_argument("--voice", type=english_voice, default="af_heart")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--prepare", action="store_true", help="Download and warm up, then exit")
    args = parser.parse_args()
    if args.threads < 1 or not 1 <= args.port <= 65535:
        parser.error("threads must be positive and port must be between 1 and 65535")
    engine = KokoroEngine(args.voice, args.device, args.threads)
    if args.prepare:
        engine.load()
        print("Kokoro model and voice are ready.")
        return 0
    import uvicorn
    uvicorn.run(create_app(engine), host=args.host, port=args.port, workers=1,
                timeout_graceful_shutdown=5)
    return 0

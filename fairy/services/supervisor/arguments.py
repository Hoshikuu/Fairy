"""Supervisor command-line options."""

from __future__ import annotations

import argparse
from pathlib import Path
from fairy.config.paths import LLAMA_MODEL, WHISPER_MODEL, KOKORO_PYTHON


def build_parser():
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
    parser.add_argument("--ready-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--ready-token", help=argparse.SUPPRESS)
    return parser


def parse_args(argv=None) -> argparse.Namespace:
    return build_parser().parse_args(argv)

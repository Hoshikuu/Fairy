"""Transcribe a WAV from the command line."""

from __future__ import annotations

import argparse
from pathlib import Path
from .whisper import transcribe_wav


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--language", default="en")
    args = parser.parse_args()
    print(transcribe_wav(args.wav, server_url=args.url, language=args.language))


if __name__ == "__main__":
    main()

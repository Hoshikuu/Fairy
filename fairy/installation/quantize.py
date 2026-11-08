"""Quantize the verified DSpark GGUF without overwriting existing files."""

import argparse
from pathlib import Path
import subprocess
import tempfile

from fairy.paths import DRAFT_MODEL, DRAFT_SOURCE, QUANTIZE


def quantize_draft(source: Path = DRAFT_SOURCE, output: Path = DRAFT_MODEL) -> None:
    if not source.is_file():
        raise RuntimeError(f"Missing draft source: {source}")
    if not QUANTIZE.is_file():
        raise RuntimeError(f"Missing llama.cpp quantizer: {QUANTIZE}")
    if output.exists():
        raise FileExistsError(f"Preserve existing output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".fairy-quantize-", dir=output.parent) as directory:
        temporary = Path(directory) / output.name
        subprocess.run([str(QUANTIZE), str(source.resolve()), str(temporary), "Q4_K_M"],
                       cwd=QUANTIZE.parent, stdin=subprocess.DEVNULL, check=True)
        if not temporary.is_file() or temporary.stat().st_size < 1024:
            raise RuntimeError("Quantization did not produce a complete GGUF")
        # Hard-link publication fails if another process created the destination.
        output.hardlink_to(temporary)
    print(f"[PASS]  Quantized draft: {output}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DRAFT_SOURCE)
    parser.add_argument("--output", type=Path, default=DRAFT_MODEL)
    args = parser.parse_args()
    try:
        quantize_draft(args.source, args.output)
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"[ERROR]  {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Shared NVIDIA detection and system metadata."""
from __future__ import annotations
import re
import shutil
import subprocess
from dataclasses import dataclass

# =========================================================
# DATA AND SYSTEM DETECTION
# =========================================================

@dataclass(frozen=True)
class SystemInfo:
    os: str
    arch: str
    gpu: str | None = None
    cuda: str | None = None


def get_nvidia() -> tuple[str | None, str | None]:
    """Return the first NVIDIA GPU name and driver-supported CUDA version."""

    if not shutil.which("nvidia-smi"):
        return None, None

    try:
        gpu = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip().splitlines()[0]

        outputs = []
        for command in (["nvidia-smi", "--version"], ["nvidia-smi"]):
            try:
                outputs.append(
                    subprocess.check_output(
                        command,
                        text=True,
                        stderr=subprocess.DEVNULL,
                    )
                )
            except (OSError, subprocess.CalledProcessError):
                pass

        cuda = None
        for output in outputs:
            match = re.search(
                r"CUDA(?:\s+UMD)?\s+Version\s*:\s*(\d+\.\d+)",
                output,
                re.IGNORECASE,
            )
            if match:
                cuda = match.group(1)
                break

        return gpu, cuda
    except (OSError, subprocess.CalledProcessError, IndexError):
        return None, None

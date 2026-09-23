"""Install reproducibly pinned Fairy models from Hugging Face.

The repository revisions, expected byte sizes and SHA-256 checksums are fixed.
The multilingual Whisper ``small`` model is included for whisper-server.

Requirements:
    pip install huggingface_hub tqdm

Examples:
    python model_setup.py --only all
    python model_setup.py --only whisper --yes
    python model_setup.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

from huggingface_hub import hf_hub_download
from tqdm import tqdm


# =========================================================
# CONFIGURATION AND DATA
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


@dataclass(frozen=True)
class Model:
    name: str
    kind: str
    repo: str
    revision: str
    filename: str
    size_bytes: int
    sha256: str


MODELS = (
    Model(
        name="Spark-X2.5-4B Q4_K_M",
        kind="llm",
        repo="XHToken/Spark-X2.5-4B-GGUF",
        revision="9826e0be84e6e6e8b9668abc91421109a1df1e2d",
        filename="Spark-X2.5-4B-Q4_K_M.gguf",
        size_bytes=2_600_224_352,
        sha256="adfcfa19a4ed6a5985da8bf565fe15f8e1a7e131d79bae2d19d48d1c40109428",
    ),
    Model(
        name="MiniCPM5-2B Q8_0",
        kind="llm",
        repo="openbmb/MiniCPM5-2B-GGUF",
        revision="2079a22f3beaa4e306449978533478fe0522f4b3",
        filename="MiniCPM5-2B-Q8_0.gguf",
        size_bytes=2_679_710_688,
        sha256="c5415f8989bf88a8288f1b55a3cc371af53c07b0faa220a63bd7a990cfaba078",
    ),
    Model(
        name="Whisper small multilingual",
        kind="whisper",
        repo="ggerganov/whisper.cpp",
        revision="5359861c739e955e79d9a303bcbc70fb988958b1",
        filename="ggml-small.bin",
        size_bytes=487_601_967,
        sha256="1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b",
    ),
)


# =========================================================
# STATUS AND INTEGRITY
# =========================================================

def model_path(model: Model) -> Path:
    return MODELS_DIR / model.filename


def has_expected_size(model: Model) -> bool:
    path = model_path(model)
    return path.is_file() and path.stat().st_size == model.size_bytes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    total = path.stat().st_size
    with path.open("rb") as file, tqdm(
        total=total,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=f"Verifying {path.name}",
        leave=False,
    ) as bar:
        for chunk in iter(lambda: file.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
            bar.update(len(chunk))
    return digest.hexdigest()


def verify_model(model: Model) -> tuple[bool, str]:
    path = model_path(model)
    if not path.is_file():
        return False, "missing"
    if path.stat().st_size != model.size_bytes:
        return False, (
            f"wrong size ({path.stat().st_size} bytes; expected {model.size_bytes})"
        )
    actual = sha256_file(path)
    if actual.lower() != model.sha256.lower():
        return False, f"SHA-256 mismatch ({actual})"
    return True, "verified"


def select_models(selection: str) -> list[Model]:
    if selection == "all":
        return list(MODELS)
    return [model for model in MODELS if model.kind == selection]


def format_size(size: int) -> str:
    return f"{size / 1024**3:.2f} GiB"


# =========================================================
# DOWNLOAD AND INSTALLATION
# =========================================================

def download_model(model: Model) -> bool:
    print(f"\nDownloading {model.name} from pinned revision {model.revision}...")
    try:
        path = Path(
            hf_hub_download(
                repo_id=model.repo,
                filename=model.filename,
                revision=model.revision,
                local_dir=MODELS_DIR,
            )
        )
        ok, detail = verify_model(model)
        if not ok:
            print(f"Integrity check failed for {model.name}: {detail}")
            return False
    except Exception as error:
        print(f"Failed to download {model.name}: {error}")
        return False

    print(f"{model.name} downloaded and verified successfully.")
    print(f"Model path: {path}")
    return True


def install_models(models: list[Model], assume_yes: bool) -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    missing = [model for model in models if not has_expected_size(model)]
    if not missing:
        print("All selected models are present with the expected sizes.")
        return 0

    total_size = sum(model.size_bytes for model in missing)
    print("Models to install:")
    for model in missing:
        print(f"  - {model.name} ({format_size(model.size_bytes)})")
        print(f"    revision: {model.revision}")
    print(f"\nRequired download size: {format_size(total_size)}")

    if not assume_yes:
        answer = input("Download the required Fairy models? [Y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Model installation cancelled.")
            return 1

    successful = sum(download_model(model) for model in missing)
    print(f"\n{successful}/{len(missing)} missing models installed successfully.")
    print(f"Models directory: {MODELS_DIR}")
    return 0 if successful == len(missing) else 1


def verify_models(models: list[Model]) -> int:
    failures = 0
    for model in models:
        ok, detail = verify_model(model)
        print(f"{'OK' if ok else 'FAIL'}: {model.name}: {detail}")
        failures += not ok
    return 0 if failures == 0 else 1


# =========================================================
# DISPLAY AND MAIN
# =========================================================

def print_models(models: list[Model]) -> None:
    print("Models:")
    for model in models:
        status = "Present" if has_expected_size(model) else "Missing or wrong size"
        print(f"\n  {model.name}")
        print(f"    Type:     {model.kind}")
        print(f"    Size:     {format_size(model.size_bytes)}")
        print(f"    Revision: {model.revision}")
        print(f"    Status:   {status}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        choices=("all", "llm", "whisper"),
        default="all",
        help="Install all models, only LLMs, or only Whisper (default: all).",
    )
    parser.add_argument("--yes", action="store_true", help="Skip confirmation.")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Hash-check selected local models without downloading anything.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = select_models(args.only)
    print("Fairy Model Installer")
    print("=====================")
    print_models(selected)
    if args.verify:
        print("\nFull integrity verification:")
        return verify_models(selected)
    return install_models(selected, args.yes)


if __name__ == "__main__":
    raise SystemExit(main())

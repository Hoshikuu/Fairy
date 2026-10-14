"""Prepare environments, install missing components and verify the local stack."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
from fairy.config.paths import BOT_PYTHON, KOKORO_PYTHON, LLAMA_SERVER, WHISPER_SERVER, MODELS_DIR
from fairy.runtime.environment import prepare_bot_environment, require_dependencies, run_python
from fairy.services.supervisor.validation import require_file, require_port
from .models.catalog import MODELS


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=("all", "bot", "llama", "whisper", "models", "kokoro"), default="all")
    parser.add_argument("--backend", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--yes", action="store_true", help="Skip binary/model download confirmation")
    parser.add_argument("--bot-python", type=Path, default=BOT_PYTHON)
    parser.add_argument("--check", action="store_true", help="Validate installed components without installing")
    parser.add_argument("--verify-models", action="store_true", help="Hash-check GGUF/GGML files")
    parser.add_argument("--warmup", action="store_true", help="Warm up Kokoro after validation")
    parser.add_argument("--force", action="store_true", help="Reinstall existing binary releases")
    parser.add_argument("--kokoro-voice", default="af_heart")
    return parser.parse_args(argv)


def check_models(*, hashes=False):
    for model in MODELS:
        path = MODELS_DIR / model.filename
        require_file(path, model.name)
        if path.stat().st_size != model.size_bytes:
            raise RuntimeError(f"Wrong model size: {path}")
        if hashes:
            digest = hashlib.sha256()
            with path.open("rb") as file:
                for chunk in iter(lambda: file.read(4 * 1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != model.sha256:
                raise RuntimeError(f"SHA-256 mismatch: {path}")
        print(f"Model ready: {model.name}" + (" (SHA-256 verified)" if hashes else ""))


def install_components(args):
    selected = {"bot", "llama", "whisper", "models", "kokoro"} if args.only == "all" else {args.only}
    if selected & {"bot", "llama", "whisper", "models"}:
        if args.check:
            require_dependencies(args.bot_python, "bot")
        else:
            prepare_bot_environment(args.bot_python)
    binary_args = ["--backend", args.backend] + (["--yes"] if args.yes else [])
    for name, executable in (("llama", LLAMA_SERVER), ("whisper", WHISPER_SERVER)):
        if name not in selected:
            continue
        if not args.check and (args.force or not executable.is_file()):
            run_python(args.bot_python, ["-m", f"fairy.installers.{name}", *binary_args],
                       timeout=900, interactive=not args.yes)
        require_file(executable, name)
        print(f"Binary ready: {executable.name}")
    if "models" in selected:
        if not args.check:
            run_python(args.bot_python, ["-m", "fairy.installers.models", *(["--yes"] if args.yes else [])],
                       timeout=1800, interactive=not args.yes)
        check_models(hashes=args.verify_models)
    if "kokoro" in selected:
        if not args.check:
            from .kokoro import main as install_kokoro
            if install_kokoro(args.kokoro_voice):
                raise RuntimeError("Kokoro installation failed")
        require_dependencies(KOKORO_PYTHON, "kokoro")
        if args.warmup and args.check:
            run_python(KOKORO_PYTHON, ["-m", "fairy.services.kokoro", "--prepare", "--voice", args.kokoro_voice])
    if args.only == "all":
        for port in (8080, 8081, 8082):
            require_port("127.0.0.1", port)
    print("Selected components are ready.")


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        if not (3, 11) <= sys.version_info[:2] < (3, 13):
            raise RuntimeError("Use Python 3.11-3.12 for asyncio.timeout and Kokoro 0.9.4; Python 3.12 is recommended")
        install_components(args)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Setup failed: {error}\n{(getattr(error, 'stderr', None) or '')[-2000:]}", file=sys.stderr)
        return 1



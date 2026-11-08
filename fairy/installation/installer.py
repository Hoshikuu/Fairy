"""Prepare the Python environment, llama.cpp and dual-model runtime."""

import argparse
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import venv
from urllib.request import Request, urlopen
from zipfile import ZipFile

from fairy.paths import ROOT, SERVER, BRAIN_MODEL, OMNI_MODEL, OMNI_PROJECTOR, DRAFT_SOURCE, DRAFT_MODEL, VENV_PYTHON
from fairy.installation.download import checksum, download
from fairy.installation.quantize import quantize_draft


RELEASE = "b11960"
ASSETS = (
    "llama-b11960-bin-win-cuda-13.4-x64.zip",
    "cudart-llama-bin-win-cuda-13.4-x64.zip",
)
DAVE_REVISION = "78fcb434a3484f2abf54cf89e80e86b651e5c28d"
DAVE_REPOSITORY = "https://github.com/jstewart0788/discord-ext-voice-recv-dave"
OMNI_MODELS = (
    (BRAIN_MODEL, "https://huggingface.co/openbmb/MiniCPM5-2B-GGUF/resolve/2079a22f3beaa4e306449978533478fe0522f4b3/MiniCPM5-2B-Q4_K_M.gguf", "ec2d5801640099e97d8d7e8003ad4d81f336e757811f03a26173dddf386602fd"),
    (OMNI_MODEL, "https://huggingface.co/LiquidAI/LFM3-Omni-2B-GGUF/resolve/main/LFM3-Omni-2B-Q4_K_M.gguf", "9f8d30e9d4fd7a9349d586e077988229b3ca0a0e4ad730897563d1eccc9893e2"),
    (OMNI_PROJECTOR, "https://huggingface.co/LiquidAI/LFM3-Omni-2B-GGUF/resolve/main/mmproj-LFM3-Omni-2B-Q4_K_M.gguf", "0a746c0794782a16d4456b230c2a0b5888a2d94a6677211edbed7d7a4177a39a"),
)
DRAFT_URL = "https://huggingface.co/openbmb/MiniCPM5-2B-DSpark-GGUF/resolve/main/MiniCPM5-2.6B-DSpark.gguf"
DRAFT_SHA256 = "57df08640f0534a1aac075d1c8bdacdb2b7e5815da6f4e5cfd39ecac3a3f0c26"


def install_dual_models(*, check: bool, hashes: bool) -> None:
    for path, url, expected in OMNI_MODELS:
        if not path.exists():
            if check:
                raise RuntimeError(f"Missing model: {path}")
            download(url, path, expected)
        if hashes or not check:
            if checksum(path) != expected:
                raise RuntimeError(f"Model SHA-256 mismatch; preserve existing file: {path}")
        elif not path.is_file() or path.stat().st_size < 1024:
            raise RuntimeError(f"Model is incomplete: {path}")
        print(f"[PASS]  Model ready: {path}")
    if not DRAFT_MODEL.exists():
        if check:
            raise RuntimeError(f"Missing quantized draft model: {DRAFT_MODEL}")
        with tempfile.TemporaryDirectory(prefix=".fairy-draft-", dir=DRAFT_MODEL.parent) as directory:
            source = Path(directory) / DRAFT_SOURCE.name
            download(DRAFT_URL, source, DRAFT_SHA256)
            quantize_draft(source, DRAFT_MODEL)
    if not DRAFT_MODEL.is_file() or DRAFT_MODEL.stat().st_size < 1024:
        raise RuntimeError(f"Quantized draft model is incomplete: {DRAFT_MODEL}")


def check_python() -> None:
    if sys.version_info[:2] != (3, 15):
        raise RuntimeError("Fairy requires Python 3.15. Run setup with Python 3.15.")


def check_environment() -> None:
    if not VENV_PYTHON.is_file():
        raise RuntimeError(f"Missing Python environment: {VENV_PYTHON}")
    result = subprocess.run(
        [str(VENV_PYTHON), "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"],
        capture_output=True, text=True, timeout=30, check=True, stdin=subprocess.DEVNULL,
    )
    if result.stdout.strip() != "3.15":
        raise RuntimeError("The existing .venv does not use Python 3.15; preserve or rename it before setup.")
    check_receiver_conflict()
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "check"], check=True, timeout=120, stdin=subprocess.DEVNULL)
    probe = (
        "import aiohttp, audioop, davey, discord, dotenv, discord.ext.voice_recv; "
        "import json; from importlib.metadata import distribution; "
        "text = distribution('discord-ext-voice-recv-dave').read_text('direct_url.json'); "
        "data = json.loads(text or '{}'); "
        "assert data.get('url', '').removesuffix('.git') == " + repr(DAVE_REPOSITORY) + "; "
        "assert data.get('vcs_info', {}).get('commit_id') == " + repr(DAVE_REVISION)
    )
    subprocess.run([str(VENV_PYTHON), "-c", probe], check=True, timeout=60, stdin=subprocess.DEVNULL)


def check_receiver_conflict() -> None:
    probe = (
        "from importlib.metadata import distribution, PackageNotFoundError; "
        "import sys; "
        "sys.exit(0 if any(d.metadata['Name'].lower().replace('_', '-') == "
        "'discord-ext-voice-recv' for d in __import__('importlib.metadata', fromlist=['distributions']).distributions()) else 1)"
    )
    result = subprocess.run([str(VENV_PYTHON), "-c", probe], timeout=30, stdin=subprocess.DEVNULL)
    if result.returncode == 0:
        raise RuntimeError(
            "Conflicting discord-ext-voice-recv is installed. Remove it first with "
            f"{VENV_PYTHON} -m pip uninstall discord-ext-voice-recv, then rerun setup."
        )
    if result.returncode != 1:
        raise RuntimeError("Could not inspect the installed Discord receiver.")


def check_llama() -> None:
    if not SERVER.is_file():
        raise RuntimeError(f"Missing llama-server: {SERVER}")
    result = subprocess.run([str(SERVER), "--version"], capture_output=True, text=True,
                            timeout=30, check=True, stdin=subprocess.DEVNULL)
    version = re.search(r"\bbuild\s+(\d+)", result.stdout + result.stderr, re.IGNORECASE)
    if not version or int(version.group(1)) < 11960:
        raise RuntimeError("llama-server must report build 11960 or newer.")
    print(f"[PASS]  llama-server build {version.group(1)}: {SERVER}")


def install_environment() -> None:
    check_python()
    directory = ROOT / ".venv"
    if not directory.exists():
        venv.EnvBuilder(with_pip=True).create(directory)
    elif not VENV_PYTHON.is_file():
        raise RuntimeError("Existing .venv is incomplete; preserve or rename it before setup.")
    result = subprocess.run(
        [str(VENV_PYTHON), "-c", "import sys; print('.'.join(map(str, sys.version_info[:2])))"],
        capture_output=True, text=True, timeout=30, check=True, stdin=subprocess.DEVNULL,
    )
    if result.stdout.strip() != "3.15":
        raise RuntimeError("Existing .venv is not Python 3.15; preserve or rename it before setup.")
    check_receiver_conflict()
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")],
                   check=True, timeout=1800, stdin=subprocess.DEVNULL)
    check_environment()


def release_assets() -> dict:
    request = Request(
        f"https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/{RELEASE}",
        headers={"User-Agent": "Fairy-installer", "Accept": "application/vnd.github+json"},
    )
    with urlopen(request, timeout=30) as response:
        release = json.load(response)
    return {item["name"]: item for item in release["assets"]}


def extract_zip(archive: Path, destination: Path) -> None:
    with ZipFile(archive) as file:
        root = destination.resolve()
        for item in file.infolist():
            target = (root / item.filename).resolve()
            if not target.is_relative_to(root) or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError(f"Unsafe archive entry: {item.filename}")
        file.extractall(root)


def install_llama() -> None:
    if SERVER.is_file():
        check_llama()
        return
    if platform.system() != "Windows" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise RuntimeError("Automatic llama.cpp installation currently supports Windows x64 with CUDA 13.4.")
    destination = SERVER.parent
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError(f"Existing llama directory is incomplete; preserve it before reinstalling: {destination}")
    assets = release_assets()
    with tempfile.TemporaryDirectory(prefix=".fairy-install-", dir=ROOT) as directory:
        temporary = Path(directory)
        unpacked = temporary / "llama"
        unpacked.mkdir()
        for name in ASSETS:
            item = assets.get(name)
            digest = item.get("digest", "") if item else ""
            if not digest.startswith("sha256:") or len(digest) != 71:
                raise RuntimeError(f"Release does not provide a SHA-256 digest for {name}")
            archive = temporary / name
            download(item["browser_download_url"], archive, digest[7:])
            extract_zip(archive, unpacked)
        if not (unpacked / SERVER.name).is_file():
            raise RuntimeError("Downloaded release does not contain llama-server.exe at its root.")
        if destination.exists():
            destination.rmdir()
        unpacked.rename(destination)
    print(f"[PASS]  Installed llama.cpp {RELEASE}: {SERVER}")
    check_llama()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check installed components without changes.")
    parser.add_argument("--verify-models", action="store_true", help="Check model SHA-256 hashes.")
    parser.add_argument("--only", choices=("all", "environment", "llama", "models", "dual-models"), default="all")
    parser.add_argument("--yes", action="store_true", help="Run without interactive prompts.")
    args = parser.parse_args(argv)
    sections = [("environment", "Python environment"), ("llama", "llama.cpp"), ("models", "LFM3 and MiniCPM models")]
    selected = [(key, label) for key, label in sections if args.only in ("all", key) or (args.only == "dual-models" and key == "models")]
    print(f"[INFO]  Fairy setup: {'check' if args.check else 'install'}", flush=True)
    try:
        for index, (key, label) in enumerate(selected, 1):
            print(f"[INFO]  {index}/{len(selected)}: {label}", flush=True)
            if key == "environment":
                check_environment() if args.check else install_environment()
            elif key == "llama":
                check_llama() if args.check else install_llama()
            else:
                install_dual_models(check=args.check, hashes=args.verify_models)
        print("[PASS]  Fairy setup complete.", flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError, KeyError) as error:
        sys.stdout.flush()
        print(f"[ERROR]  Setup failed: {error}", file=sys.stderr)
        return 1

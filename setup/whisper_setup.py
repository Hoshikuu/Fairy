"""Install the pinned whisper.cpp b5130 release for Fairy.

The installer selects only real b5130 assets.  Use ``--backend cpu`` to keep
Whisper off the GPU and leave VRAM available for llama.cpp.  Every selected
archive is checked against the size and SHA-256 published by GitHub.

Requirements:
    pip install requests tqdm

Examples:
    python whisper_setup.py --dry-run
    python whisper_setup.py --backend cpu
    python whisper_setup.py --backend auto --yes
"""

from __future__ import annotations

import argparse
import hashlib
import platform
import re
import shlex
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import requests
from tqdm import tqdm


# =========================================================
# CONFIGURATION
# =========================================================

REPO = "ggml-org/whisper.cpp"
RELEASE_TAG = "b5130"
GITHUB_API = f"https://api.github.com/repos/{REPO}/releases/tags/{RELEASE_TAG}"
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/{RELEASE_TAG}/"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WHISPER_DIR = PROJECT_ROOT / "whisper"
MODELS_DIR = PROJECT_ROOT / "models"
DEFAULT_MODEL = MODELS_DIR / "ggml-small.bin"

HTTP_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Fairy-whisper-installer",
}


# =========================================================
# DATA AND SYSTEM DETECTION
# =========================================================

@dataclass(frozen=True)
class SystemInfo:
    os: str
    arch: str
    gpu: str | None = None
    cuda: str | None = None


def get_arch() -> str:
    """Return the architecture using b5130 asset naming."""

    machine = platform.machine().lower()
    aliases = {
        "amd64": "x64",
        "x86_64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64",
        "x86": "x86",
        "i386": "x86",
        "i686": "x86",
    }
    return aliases.get(machine, machine)


def get_nvidia() -> tuple[str | None, str | None]:
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


def get_system() -> SystemInfo:
    gpu, cuda = get_nvidia()
    return SystemInfo(platform.system().lower(), get_arch(), gpu, cuda)


# =========================================================
# RELEASE AND ASSET SELECTION
# =========================================================

def get_release() -> dict:
    response = requests.get(GITHUB_API, headers=HTTP_HEADERS, timeout=20)
    response.raise_for_status()
    release = response.json()
    if release.get("tag_name") != RELEASE_TAG or release.get("draft"):
        raise RuntimeError(
            f"GitHub did not return the expected non-draft release {RELEASE_TAG}."
        )
    return release


def asset_info(asset: dict) -> dict:
    url = asset["browser_download_url"]
    if not url.startswith(DOWNLOAD_PREFIX):
        raise RuntimeError(f"Unexpected asset URL outside {RELEASE_TAG}: {url}")
    digest = asset.get("digest") or ""
    sha256 = digest.removeprefix("sha256:") if digest.startswith("sha256:") else None
    return {
        "name": asset["name"],
        "url": url,
        "size": int(asset["size"]),
        "sha256": sha256,
    }


def find_exact_asset(release: dict, filename: str) -> dict | None:
    for asset in release.get("assets", []):
        if asset["name"].lower() == filename.lower():
            return asset_info(asset)
    return None


def version_tuple(version: str) -> tuple[int, int]:
    match = re.match(r"(\d+)(?:\.(\d+))?", version)
    if not match:
        return 0, 0
    return int(match.group(1)), int(match.group(2) or 0)


def find_windows_x64_cuda(release: dict, supported_cuda: str) -> dict | None:
    pattern = re.compile(
        r"^whisper-cublas-(\d+)\.(\d+)(?:\.\d+)?-bin-x64\.zip$",
        re.IGNORECASE,
    )
    supported = version_tuple(supported_cuda)
    candidates: list[tuple[tuple[int, int], dict]] = []
    for asset in release.get("assets", []):
        match = pattern.match(asset["name"])
        if not match:
            continue
        version = int(match.group(1)), int(match.group(2))
        if version <= supported:
            candidates.append((version, asset))

    if not candidates:
        return None
    version, asset = max(candidates, key=lambda item: item[0])
    info = asset_info(asset)
    info["cuda"] = f"{version[0]}.{version[1]}"
    return info


def select_build(system: SystemInfo, release: dict, preference: str) -> dict:
    """Choose only combinations that b5130 actually publishes."""

    if preference == "cuda" and (not system.gpu or not system.cuda):
        raise RuntimeError(
            "CUDA was requested, but nvidia-smi did not report a usable NVIDIA GPU "
            "and driver-supported CUDA version."
        )

    if system.os == "windows":
        if preference in {"auto", "cuda"} and system.gpu and system.cuda:
            cuda_asset = None
            if system.arch == "x64":
                cuda_asset = find_windows_x64_cuda(release, system.cuda)
            elif system.arch == "arm64" and version_tuple(system.cuda) >= (13, 4):
                cuda_asset = find_exact_asset(
                    release, "whisper-bin-win-cuda-13.4-arm64.zip"
                )
                if cuda_asset:
                    cuda_asset["cuda"] = "13.4"

            if cuda_asset:
                return {
                    "backend": "cuda",
                    "cuda": cuda_asset["cuda"],
                    "packages": [cuda_asset],
                }
            if preference == "cuda":
                raise RuntimeError(
                    f"Release {RELEASE_TAG} has no CUDA asset compatible with "
                    f"Windows {system.arch} and CUDA {system.cuda}."
                )

        if preference in {"auto", "cpu"}:
            cpu_assets = {
                "x64": "whisper-bin-x64.zip",
                "x86": "whisper-bin-Win32.zip",
                "arm64": "whisper-bin-win-cpu-arm64.zip",
            }
            filename = cpu_assets.get(system.arch)
            asset = find_exact_asset(release, filename) if filename else None
            if asset:
                notice = None
                if preference == "auto" and system.gpu:
                    notice = "No compatible CUDA asset was published; using CPU."
                return {
                    "backend": "cpu",
                    "packages": [asset],
                    "notice": notice,
                }

    elif system.os == "linux":
        if preference == "cuda":
            raise RuntimeError(
                f"Release {RELEASE_TAG} publishes no Linux CUDA archive; use "
                "--backend cpu or build whisper.cpp from source."
            )
        filename = f"whisper-bin-ubuntu-{system.arch}.tar.gz"
        asset = find_exact_asset(release, filename)
        if asset:
            notice = None
            if system.gpu:
                notice = (
                    f"Release {RELEASE_TAG} has no Linux CUDA asset; using CPU."
                )
            return {
                "backend": "cpu",
                "packages": [asset],
                "notice": notice,
            }

    elif system.os == "darwin":
        raise RuntimeError(
            f"Release {RELEASE_TAG} publishes an Apple XCFramework, but no macOS "
            "whisper-server executable. Build from source on macOS."
        )

    raise RuntimeError(
        f"Release {RELEASE_TAG} has no compatible {preference} server build for "
        f"{system.os} {system.arch}."
    )


# =========================================================
# DOWNLOAD AND INSTALLATION
# =========================================================

def format_size(size: int) -> str:
    if size >= 1024**3:
        return f"{size / 1024**3:.2f} GB"
    return f"{size / 1024**2:.2f} MB"


def archive_name(asset: dict, index: int) -> str:
    suffix = ".tar.gz" if asset["name"].lower().endswith(".tar.gz") else ".zip"
    return f"package_{index}{suffix}"


def download(asset: dict, destination: Path) -> None:
    digest = hashlib.sha256()
    written = 0
    with requests.get(
        asset["url"],
        stream=True,
        timeout=(20, 180),
        headers=HTTP_HEADERS,
    ) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", asset["size"]))
        with destination.open("wb") as file, tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=asset["name"],
        ) as bar:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                file.write(chunk)
                digest.update(chunk)
                written += len(chunk)
                bar.update(len(chunk))

    if written != asset["size"]:
        raise RuntimeError(
            f"Size mismatch for {asset['name']}: expected {asset['size']}, got {written}."
        )
    if asset["sha256"] and digest.hexdigest().lower() != asset["sha256"].lower():
        raise RuntimeError(f"SHA-256 mismatch for {asset['name']}.")


def find_server(root: Path) -> Path | None:
    names = {"whisper-server", "whisper-server.exe"}
    return next((path for path in root.rglob("*") if path.name in names), None)


def replace_installation(staged: Path) -> None:
    backup = PROJECT_ROOT / f".whisper-backup-{uuid.uuid4().hex}"
    had_existing = WHISPER_DIR.exists()
    if had_existing:
        WHISPER_DIR.rename(backup)

    try:
        shutil.move(str(staged), str(WHISPER_DIR))
    except Exception:
        if WHISPER_DIR.exists():
            shutil.rmtree(WHISPER_DIR)
        if had_existing and backup.exists():
            backup.rename(WHISPER_DIR)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)


def command_line(server: Path, model: Path) -> str:
    args = [
        str(server),
        "--host",
        "127.0.0.1",
        "--port",
        "8080",
        "--model",
        str(model),
    ]
    if platform.system().lower() == "windows":
        return subprocess.list2cmdline(args)
    return shlex.join(args)


def install(build: dict, assume_yes: bool) -> bool:
    packages = build["packages"]
    total_size = sum(package["size"] for package in packages)
    print(f"\nRequired download size: {format_size(total_size)}")

    if not assume_yes:
        answer = input("Download and install these packages? [Y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Installation cancelled.")
            return False

    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fairy_whisper_") as temp:
        temp_dir = Path(temp)
        staged = temp_dir / "install"
        staged.mkdir()
        archives: list[Path] = []

        print("\nDownloading and verifying packages...")
        for index, package in enumerate(packages, start=1):
            path = temp_dir / archive_name(package, index)
            download(package, path)
            archives.append(path)

        print("\nExtracting packages...")
        for archive in archives:
            shutil.unpack_archive(archive, staged)

        if not find_server(staged):
            raise RuntimeError("The selected archive does not contain whisper-server.")
        replace_installation(staged)

    server = find_server(WHISPER_DIR)
    print(f"\nwhisper.cpp {RELEASE_TAG} installed successfully.")
    print(f"Installation directory: {WHISPER_DIR}")
    print(f"Server executable:      {server}")
    if DEFAULT_MODEL.exists():
        print("\nLocal-only HTTP server command:")
        print(f"  {command_line(server, DEFAULT_MODEL)}")
        print("Endpoint: http://127.0.0.1:8080/inference")
    else:
        print(
            f"\nModel not found at {DEFAULT_MODEL}. Run model_setup.py first, "
            "then start whisper-server with --model pointing to a GGML model."
        )
    return True


# =========================================================
# DISPLAY AND MAIN
# =========================================================

def print_system(system: SystemInfo) -> None:
    print("System detected:")
    print(f"  OS:   {system.os}")
    print(f"  ARCH: {system.arch}")
    print(f"  GPU:  {system.gpu or 'Not detected'}")
    print(f"  CUDA: {system.cuda or 'Not detected'}")


def print_build(build: dict) -> None:
    print(f"\nPinned release: {RELEASE_TAG}")
    print(f"Selected backend: {build['backend']}")
    if build.get("cuda"):
        print(f"Selected CUDA build: {build['cuda']}")
    if build.get("notice"):
        print(f"Note: {build['notice']}")
    print("Packages:")
    for package in build["packages"]:
        checksum = package["sha256"] or "not published"
        print(f"  - {package['name']} ({format_size(package['size'])})")
        print(f"    SHA-256: {checksum}")
        print(f"    {package['url']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        choices=("auto", "cpu", "cuda"),
        default="auto",
        help="Use CPU to save VRAM, CUDA for NVIDIA, or auto (default).",
    )
    parser.add_argument("--yes", action="store_true", help="Skip confirmation.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect and select assets without downloading them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(f"Fairy whisper.cpp Installer ({RELEASE_TAG})")
    print("=======================================")
    try:
        system = get_system()
        print_system(system)
        release = get_release()
        build = select_build(system, release, args.backend)
        print_build(build)
        if args.dry_run:
            print("\nDry run completed; nothing was downloaded or changed.")
            return 0
        return 0 if install(build, args.yes) else 1
    except (requests.RequestException, OSError, RuntimeError, shutil.ReadError) as error:
        print(f"\nInstallation failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

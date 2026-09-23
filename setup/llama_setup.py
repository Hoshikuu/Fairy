"""Install a pinned llama.cpp release for Fairy.

The release is intentionally fixed to b11115.  The installer detects the
operating system, CPU architecture and the maximum CUDA version supported by
the NVIDIA driver, then selects only assets that actually belong to b11115.

Requirements:
    pip install requests tqdm

Examples:
    python llama_setup.py --dry-run
    python llama_setup.py --backend auto
    python llama_setup.py --backend cpu --yes
"""

from __future__ import annotations

import argparse
import hashlib
import platform
import re
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

REPO = "ggml-org/llama.cpp"
RELEASE_TAG = "b11115"
GITHUB_API = f"https://api.github.com/repos/{REPO}/releases/tags/{RELEASE_TAG}"
DOWNLOAD_PREFIX = f"https://github.com/{REPO}/releases/download/{RELEASE_TAG}/"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LLAMA_DIR = PROJECT_ROOT / "llama"

HTTP_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Fairy-llama-installer",
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
    """Return the CPU architecture using llama.cpp asset names."""

    machine = platform.machine().lower()
    aliases = {
        "amd64": "x64",
        "x86_64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64",
        "s390x": "s390x",
    }
    return aliases.get(machine, machine)


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


def get_system() -> SystemInfo:
    gpu, cuda = get_nvidia()
    return SystemInfo(
        os=platform.system().lower(),
        arch=get_arch(),
        gpu=gpu,
        cuda=cuda,
    )


# =========================================================
# RELEASE AND ASSET SELECTION
# =========================================================

def get_release() -> dict:
    """Fetch and validate exactly the pinned release."""

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


def find_cuda_build(
    release: dict,
    supported_cuda: str,
    os_name: str,
    arch: str,
) -> dict | None:
    """Select the newest b11115 CUDA package supported by the driver."""

    platform_name = "win" if os_name == "windows" else "ubuntu"
    extension = r"\.zip" if os_name == "windows" else r"\.tar\.gz"
    pattern = re.compile(
        rf"^llama-{RELEASE_TAG}-bin-{platform_name}-cuda-"
        rf"(\d+)\.(\d+)-{re.escape(arch)}{extension}$",
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


def find_cuda_runtime(
    release: dict,
    cuda: str,
    os_name: str,
    arch: str,
) -> dict | None:
    platform_name = "win" if os_name == "windows" else "ubuntu"
    extension = r"\.zip" if os_name == "windows" else r"\.tar\.gz"
    pattern = re.compile(
        rf"^cudart-llama(?:-{RELEASE_TAG})?-bin-{platform_name}-cuda-"
        rf"{re.escape(cuda)}-{re.escape(arch)}{extension}$",
        re.IGNORECASE,
    )
    for asset in release.get("assets", []):
        if pattern.match(asset["name"]):
            return asset_info(asset)
    return None


def select_build(system: SystemInfo, release: dict, preference: str) -> dict:
    """Select a verified asset set for auto, CPU or CUDA mode."""

    if preference == "cuda" and (not system.gpu or not system.cuda):
        raise RuntimeError(
            "CUDA was requested, but nvidia-smi did not report a usable NVIDIA GPU "
            "and driver-supported CUDA version."
        )

    if system.os in {"windows", "linux"}:
        if preference in {"auto", "cuda"} and system.gpu and system.cuda:
            llama = find_cuda_build(
                release, system.cuda, system.os, system.arch
            )
            if llama:
                runtime = find_cuda_runtime(
                    release, llama["cuda"], system.os, system.arch
                )
                if runtime:
                    return {
                        "backend": "cuda",
                        "cuda": llama["cuda"],
                        "packages": [llama, runtime],
                    }

            if preference == "cuda":
                raise RuntimeError(
                    f"Release {RELEASE_TAG} has no complete CUDA build compatible "
                    f"with {system.os} {system.arch} and CUDA {system.cuda}."
                )

        if preference in {"auto", "cpu"}:
            platform_name = "win-cpu" if system.os == "windows" else "ubuntu"
            extension = ".zip" if system.os == "windows" else ".tar.gz"
            filename = (
                f"llama-{RELEASE_TAG}-bin-{platform_name}-{system.arch}{extension}"
            )
            llama = find_exact_asset(release, filename)
            if llama:
                notice = None
                if preference == "auto" and system.gpu:
                    notice = (
                        "No compatible complete CUDA pair was published; using CPU."
                    )
                return {
                    "backend": "cpu",
                    "packages": [llama],
                    "notice": notice,
                }

    elif system.os == "darwin":
        if preference == "cuda":
            raise RuntimeError("CUDA packages are not available for macOS.")
        filename = f"llama-{RELEASE_TAG}-bin-macos-{system.arch}.tar.gz"
        llama = find_exact_asset(release, filename)
        if llama:
            return {
                "backend": "metal" if system.arch == "arm64" else "cpu",
                "packages": [llama],
            }

    raise RuntimeError(
        f"Release {RELEASE_TAG} has no compatible {preference} build for "
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
    """Download an asset and verify its size and published SHA-256."""

    digest = hashlib.sha256()
    written = 0
    with requests.get(
        asset["url"],
        stream=True,
        timeout=(20, 120),
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
    names = {"llama-server", "llama-server.exe"}
    return next((path for path in root.rglob("*") if path.name in names), None)


def replace_installation(staged: Path) -> None:
    backup = PROJECT_ROOT / f".llama-backup-{uuid.uuid4().hex}"
    had_existing = LLAMA_DIR.exists()
    if had_existing:
        LLAMA_DIR.rename(backup)

    try:
        shutil.move(str(staged), str(LLAMA_DIR))
    except Exception:
        if LLAMA_DIR.exists():
            shutil.rmtree(LLAMA_DIR)
        if had_existing and backup.exists():
            backup.rename(LLAMA_DIR)
        raise
    else:
        if backup.exists():
            shutil.rmtree(backup)


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
    with tempfile.TemporaryDirectory(prefix="fairy_llama_") as temp:
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
            raise RuntimeError("The selected archives do not contain llama-server.")
        replace_installation(staged)

    server = find_server(LLAMA_DIR)
    print(f"\nllama.cpp {RELEASE_TAG} installed successfully.")
    print(f"Installation directory: {LLAMA_DIR}")
    print(f"Server executable:      {server}")
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
        help="Backend preference (default: auto).",
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
    print(f"Fairy llama.cpp Installer ({RELEASE_TAG})")
    print("=====================================")
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

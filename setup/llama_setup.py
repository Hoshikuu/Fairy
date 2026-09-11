"""
llama.cpp automatic installer.

Features:
- Detects operating system and CPU architecture.
- Detects NVIDIA GPU and maximum CUDA version supported by the driver.
- Retrieves the latest llama.cpp GitHub release, including pre-releases.
- Selects the most appropriate precompiled llama.cpp package.
- Selects the newest compatible CUDA build when available.
- Downloads required packages with progress bars.
- Uses the operating system temporary directory for downloads.
- Installs everything into ./llama/.
- Automatically removes temporary downloaded files.

Requirements:
    pip install requests tqdm

Supported platforms:
- Windows x64 / arm64
    - NVIDIA CUDA when available
    - CPU fallback
- macOS x64 / arm64
- Linux x64 / arm64 / s390x

The installer does not require the CUDA Toolkit to be installed.
For precompiled CUDA builds, only a compatible NVIDIA driver is required.
"""

import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests
from tqdm import tqdm


# =========================================================
# CONFIGURATION
# =========================================================

REPO = "ggml-org/llama.cpp"

GITHUB_API = (
    f"https://api.github.com/repos/{REPO}/releases"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LLAMA_DIR = PROJECT_ROOT / "llama"

HTTP_HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Fairy-llama-installer"
}


# =========================================================
# DATA
# =========================================================

@dataclass
class SystemInfo:
    os: str
    arch: str
    gpu: str | None = None
    cuda: str | None = None


# =========================================================
# SYSTEM DETECTION
# =========================================================

def get_arch() -> str:
    """Return the current CPU architecture in llama.cpp naming format."""

    arch = platform.machine().lower()

    aliases = {
        "amd64": "x64",
        "x86_64": "x64",
        "arm64": "arm64",
        "aarch64": "arm64",
        "s390x": "s390x"
    }

    return aliases.get(arch, arch)


def get_nvidia() -> tuple[str | None, str | None]:
    """
    Detect an NVIDIA GPU and the maximum CUDA version supported
    by the installed NVIDIA driver.

    Returns:
        (GPU name, CUDA version)

    Example:
        ("NVIDIA GeForce RTX 4060", "13.4")
    """

    if not shutil.which("nvidia-smi"):
        return None, None

    try:
        gpu = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name",
                "--format=csv,noheader"
            ],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip().splitlines()[0]

        output = subprocess.check_output(
            ["nvidia-smi", "--version"],
            text=True,
            stderr=subprocess.DEVNULL
        )

        cuda = None

        # New NVIDIA drivers:
        # CUDA UMD version : 13.4
        match = re.search(
            r"CUDA UMD.*?(\d+\.\d+)",
            output,
            re.IGNORECASE
        )

        if match:
            cuda = match.group(1)

        # Older NVIDIA drivers.
        if not cuda:
            for line in output.splitlines():

                if "CUDA" not in line.upper():
                    continue

                if "DEPRECATED" in line.upper():
                    continue

                match = re.search(
                    r"(\d+\.\d+)",
                    line
                )

                if match:
                    cuda = match.group(1)
                    break

        # Extra fallback using normal nvidia-smi output.
        if not cuda:
            output = subprocess.check_output(
                ["nvidia-smi"],
                text=True,
                stderr=subprocess.DEVNULL
            )

            match = re.search(
                r"CUDA Version:\s*(\d+\.\d+)",
                output,
                re.IGNORECASE
            )

            if match:
                cuda = match.group(1)

        return gpu, cuda

    except (
        OSError,
        subprocess.CalledProcessError,
        IndexError
    ):
        return None, None


def get_system() -> SystemInfo:
    """Detect operating system, architecture and NVIDIA information."""

    gpu, cuda = get_nvidia()

    return SystemInfo(
        os=platform.system().lower(),
        arch=get_arch(),
        gpu=gpu,
        cuda=cuda
    )


# =========================================================
# GITHUB
# =========================================================

def get_latest_release() -> dict | None:
    """
    Return the newest non-draft llama.cpp release.

    Pre-releases are intentionally accepted because llama.cpp
    publishes its regular binary builds as pre-releases.
    """

    response = requests.get(
        GITHUB_API,
        headers=HTTP_HEADERS,
        timeout=15
    )

    response.raise_for_status()

    for release in response.json():

        if not release.get("draft"):
            return release

    return None


# =========================================================
# ASSETS
# =========================================================

def asset_info(asset: dict) -> dict:
    """Return only the asset information needed by the installer."""

    return {
        "name": asset["name"],
        "url": asset["browser_download_url"],
        "size": asset["size"]
    }


def find_asset(
    release: dict,
    *patterns: str
) -> dict | None:
    """Find a release asset containing all supplied patterns."""

    patterns = tuple(
        pattern.lower()
        for pattern in patterns
    )

    for asset in release.get("assets", []):

        name = asset["name"].lower()

        if all(
            pattern in name
            for pattern in patterns
        ):
            return asset_info(asset)

    return None


def version_tuple(version: str) -> tuple[int, int]:
    """Convert '13.4' into (13, 4)."""

    match = re.match(
        r"(\d+)(?:\.(\d+))?",
        version
    )

    if not match:
        return 0, 0

    return (
        int(match.group(1)),
        int(match.group(2) or 0)
    )


def find_cuda_build(
    release: dict,
    supported_cuda: str,
    arch: str
) -> dict | None:
    """
    Find the newest Windows CUDA build compatible with
    the CUDA version supported by the NVIDIA driver.

    Example:
        Driver supports: 13.4

        Available:
            12.4
            13.3
            13.5

        Selected:
            13.3
    """

    supported = version_tuple(
        supported_cuda
    )

    candidates = []

    pattern = re.compile(
        rf"llama-.+?-bin-win-cuda-"
        rf"(\d+)\.(\d+)-{re.escape(arch)}\.zip$",
        re.IGNORECASE
    )

    for asset in release.get("assets", []):

        match = pattern.match(
            asset["name"]
        )

        if not match:
            continue

        version = (
            int(match.group(1)),
            int(match.group(2))
        )

        if version <= supported:
            candidates.append(
                (version, asset)
            )

    if not candidates:
        return None

    version, asset = max(
        candidates,
        key=lambda item: item[0]
    )

    info = asset_info(asset)

    info["cuda"] = (
        f"{version[0]}.{version[1]}"
    )

    return info


def find_cuda_runtime(
    release: dict,
    cuda: str,
    arch: str
) -> dict | None:
    """Find the CUDA runtime matching a llama.cpp CUDA build."""

    filename = (
        f"cudart-llama-bin-win-cuda-"
        f"{cuda}-{arch}.zip"
    )

    for asset in release.get("assets", []):

        if asset["name"].lower() == filename.lower():
            return asset_info(asset)

    return None


# =========================================================
# BUILD SELECTION
# =========================================================

def select_build(
    system: SystemInfo,
    release: dict
) -> dict:
    """Select the best llama.cpp build for the current computer."""

    # Windows
    if system.os == "windows":

        # Prefer CUDA when NVIDIA is available.
        if system.gpu and system.cuda:

            llama = find_cuda_build(
                release,
                system.cuda,
                system.arch
            )

            if llama:
                runtime = find_cuda_runtime(
                    release,
                    llama["cuda"],
                    system.arch
                )

                # CUDA builds normally require both packages.
                if runtime:
                    return {
                        "backend": "cuda",
                        "cuda": llama["cuda"],
                        "packages": [
                            llama,
                            runtime
                        ]
                    }

        # CPU fallback.
        llama = find_asset(
            release,
            "bin-win-cpu",
            system.arch,
            ".zip"
        )

        if llama:
            return {
                "backend": "cpu",
                "packages": [llama]
            }

    # macOS
    elif system.os == "darwin":

        llama = find_asset(
            release,
            "bin-macos",
            system.arch,
            ".tar.gz"
        )

        if llama:
            return {
                "backend": (
                    "metal"
                    if system.arch == "arm64"
                    else "cpu"
                ),
                "packages": [llama]
            }

    # Linux
    elif system.os == "linux":

        llama = find_asset(
            release,
            "bin-ubuntu",
            system.arch,
            ".tar.gz"
        )

        if llama:
            return {
                "backend": "cpu",
                "packages": [llama]
            }

    raise RuntimeError(
        f"No compatible llama.cpp build was found for "
        f"{system.os} {system.arch}."
    )


# =========================================================
# DOWNLOAD
# =========================================================

def format_size(size: int) -> str:
    """Convert bytes to a readable size."""

    gb = size / 1024**3

    if gb >= 1:
        return f"{gb:.2f} GB"

    return (
        f"{size / 1024**2:.2f} MB"
    )


def download(
    asset: dict,
    destination: Path
) -> None:
    """Download a GitHub release asset with a progress bar."""

    with requests.get(
        asset["url"],
        stream=True,
        timeout=(15, 60),
        headers=HTTP_HEADERS
    ) as response:

        response.raise_for_status()

        total = int(
            response.headers.get(
                "content-length",
                asset["size"]
            )
        )

        with (
            destination.open("wb") as file,
            tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=asset["name"],
                leave=True
            ) as bar
        ):

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if not chunk:
                    continue

                file.write(chunk)
                bar.update(len(chunk))


# =========================================================
# INSTALLATION
# =========================================================

def archive_name(
    asset: dict,
    index: int
) -> str:
    """
    Generate a generic temporary filename while preserving
    the archive extension.
    """

    name = asset["name"].lower()

    if name.endswith(".tar.gz"):
        return f"package_{index}.tar.gz"

    return f"package_{index}.zip"


def install(build: dict) -> bool:
    """
    Ask the user for confirmation, download all required
    packages and install llama.cpp into ./llama/.
    """

    packages = build["packages"]

    total_size = sum(
        package["size"]
        for package in packages
    )

    print()
    print(
        f"Required download size: "
        f"{format_size(total_size)}"
    )

    answer = input(
        "Do you want to download the packages required "
        f"to install llama.cpp "
        f"({format_size(total_size)} total)? "
        "[Y/N]: "
    ).strip().lower()

    if answer not in ("y", "yes"):
        print("Installation cancelled.")
        return False

    # Everything downloaded here is automatically deleted
    # when the installation finishes.
    with tempfile.TemporaryDirectory(
        prefix="fairy_llama_"
    ) as temp:

        temp_dir = Path(temp)
        archives = []

        print()
        print("Downloading packages...")

        # Download everything before modifying an existing
        # llama installation.
        for index, package in enumerate(
            packages,
            start=1
        ):
            path = (
                temp_dir
                / archive_name(package, index)
            )

            download(
                package,
                path
            )

            archives.append(path)

        print()
        print("Downloads completed.")

        # Only replace the current installation once all
        # packages have downloaded successfully.
        if LLAMA_DIR.exists():
            shutil.rmtree(LLAMA_DIR)

        LLAMA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        print(
            f"Installing to: {LLAMA_DIR}"
        )

        for archive in archives:
            print(
                f"Extracting {archive.name}..."
            )

            shutil.unpack_archive(
                archive,
                LLAMA_DIR
            )

    print()
    print(
        "llama.cpp installation completed successfully."
    )

    print(
        f"Installation directory: {LLAMA_DIR}"
    )

    return True


# =========================================================
# DISPLAY
# =========================================================

def print_system(system: SystemInfo) -> None:
    """Print detected system information."""

    print("System detected:")
    print(f"  OS:   {system.os}")
    print(f"  ARCH: {system.arch}")
    print(
        f"  GPU:  "
        f"{system.gpu or 'Not detected'}"
    )
    print(
        f"  CUDA: "
        f"{system.cuda or 'Not detected'}"
    )


def print_build(build: dict) -> None:
    """Print the selected llama.cpp build."""

    print("Recommended llama.cpp build:")
    print(
        f"  Backend: {build['backend']}"
    )

    if build.get("cuda"):
        print(
            f"  CUDA:    {build['cuda']}"
        )

    print()

    for package in build["packages"]:
        print(
            f"  {package['name']}"
        )
        print(
            f"  {format_size(package['size'])}"
        )
        print(
            f"  {package['url']}"
        )
        print()


# =========================================================
# MAIN
# =========================================================

def main():
    try:
        print("Detecting system...")
        print()

        system = get_system()

        print_system(system)

        print()
        print(
            "Checking llama.cpp releases..."
        )

        release = get_latest_release()

        if not release:
            print(
                "No llama.cpp release was found."
            )
            return

        print(
            f"Release: {release['tag_name']}"
        )

        print(
            "Release type: "
            + (
                "pre-release"
                if release.get("prerelease")
                else "stable"
            )
        )

        print()
        print(
            "Selecting llama.cpp build..."
        )
        print()

        build = select_build(
            system,
            release
        )

        print_build(build)

        install(build)

    except requests.RequestException as error:
        print()
        print(
            f"Network error: {error}"
        )

    except RuntimeError as error:
        print()
        print(
            f"Installation error: {error}"
        )

    except KeyboardInterrupt:
        print()
        print()
        print(
            "Installation cancelled by user."
        )


if __name__ == "__main__":
    main()
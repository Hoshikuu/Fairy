"""Archive naming, streaming downloads and published checksum checks."""
import hashlib
from pathlib import Path
import requests
from tqdm import tqdm

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


def download(asset: dict, destination: Path, *, headers, read_timeout=120) -> None:
    """Download an asset and verify its size and published SHA-256."""

    digest = hashlib.sha256()
    written = 0
    with requests.get(
        asset["url"],
        stream=True,
        timeout=(20, read_timeout),
        headers=headers,
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

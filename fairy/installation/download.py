from hashlib import sha256
from pathlib import Path
from urllib.request import Request, urlopen
from fairy.installation.progress import Progress


def checksum(filepath: Path) -> str:
    digest = sha256()
    progress = Progress(f"Verifying {filepath.name}", filepath.stat().st_size)
    try:
        with filepath.open("rb") as file:
            total = 0
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
                total += len(chunk)
                progress.update(total)
    except BaseException:
        progress.abort()
        raise
    progress.finish()
    return digest.hexdigest()


def download(url: str, destination: Path, expected: str) -> None:
    """Download into a temporary file and publish only a verified artifact."""
    import tempfile
    import os

    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".fairy-download-", dir=destination.parent)
    temporary = Path(name)
    try:
        request = Request(url, headers={"User-Agent": "Fairy-installer"})
        digest = sha256()
        with os.fdopen(handle, "wb") as file, urlopen(request, timeout=120) as response:
            length = response.headers.get("Content-Length", "")
            progress = Progress(f"Downloading {destination.name}", int(length) if length.isdigit() else None)
            try:
                total = 0
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    file.write(chunk)
                    total += len(chunk)
                    progress.update(total)
            except BaseException:
                progress.abort()
                raise
            progress.finish()
        if digest.hexdigest() != expected.lower():
            raise RuntimeError(f"SHA-256 mismatch for {destination.name}")
        if destination.exists():
            raise FileExistsError(f"File appeared during download: {destination}")
        temporary.rename(destination)
    finally:
        temporary.unlink(missing_ok=True)

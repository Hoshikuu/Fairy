"""Create a dedicated CPU environment and preload Kokoro's English voice."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".venv-kokoro"
PYTHON = ENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def main() -> int:
    if not (3, 10) <= sys.version_info[:2] < (3, 14):
        print("Kokoro needs Python 3.10-3.13; Python 3.12 is recommended.", file=sys.stderr)
        return 1
    try:
        if not PYTHON.is_file():
            subprocess.run([sys.executable, "-m", "venv", str(ENV)], check=True)
        subprocess.run([str(PYTHON), "-m", "pip", "install", "torch>=2.6,<3",
                        "--index-url", "https://download.pytorch.org/whl/cpu"], check=True)
        subprocess.run([str(PYTHON), "-m", "pip", "install", "-r",
                        str(ROOT / "requirements-kokoro.txt")], check=True)
        # Misaki otherwise tries to install this on first HTTP startup.
        subprocess.run([str(PYTHON), "-m", "spacy", "download", "en_core_web_sm"], check=True)
        subprocess.run([str(PYTHON), str(ROOT / "kokoro_server.py"), "--prepare"], check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Kokoro setup failed: {error}", file=sys.stderr)
        return 1
    print(f"Kokoro installed in {ENV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

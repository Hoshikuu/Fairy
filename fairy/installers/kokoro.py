"""Create a dedicated CPU environment and preload Kokoro's English voice."""

import subprocess
import sys

from fairy.config.paths import PROJECT_ROOT as ROOT
ENV = ROOT / ".venv-kokoro"
PYTHON = ENV / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def main(voice="af_heart") -> int:
    if not (3, 10) <= sys.version_info[:2] < (3, 13):
        print("Kokoro 0.9.4 needs Python 3.10-3.12; Python 3.12 is recommended.", file=sys.stderr)
        return 1
    try:
        if not PYTHON.is_file():
            subprocess.run([sys.executable, "-m", "venv", str(ENV)], check=True, cwd=ROOT)
        subprocess.run([str(PYTHON), "-m", "pip", "install", "torch>=2.6,<3",
                        "--index-url", "https://download.pytorch.org/whl/cpu"], check=True, cwd=ROOT)
        subprocess.run([str(PYTHON), "-m", "pip", "install", "-r",
                        str(ROOT / "requirements-kokoro.txt")], check=True, cwd=ROOT)
        # Misaki otherwise tries to install this on first HTTP startup.
        subprocess.run([str(PYTHON), "-m", "spacy", "download", "en_core_web_sm"], check=True, cwd=ROOT)
        subprocess.run([str(PYTHON), "-m", "fairy.services.kokoro", "--prepare", "--voice", voice], check=True, cwd=ROOT)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Kokoro setup failed: {error}", file=sys.stderr)
        return 1
    print(f"Kokoro installed in {ENV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

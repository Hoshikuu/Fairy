"""Launch Fairy's Electron desktop application."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

from fairy.paths import ROOT


def find_npm() -> str | None:
    found = shutil.which("npm.cmd") or shutil.which("npm")
    if found:
        return found
    candidate = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs" / "npm.cmd"
    return str(candidate) if candidate.is_file() else None


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check prerequisites without starting models.")
    args = parser.parse_args()
    npm = find_npm()
    if not npm:
        print("[ERROR] Node.js and npm are required.", file=sys.stderr)
        return 1
    if not (ROOT / "desktop" / "node_modules" / "electron" / "dist" / "electron.exe").is_file():
        print("[ERROR] Electron executable is missing. Run npm install in desktop/.", file=sys.stderr)
        return 1
    if args.check:
        from fairy.installation.installer import check_environment, check_llama
        from fairy.runner.dual import brain_settings, omni_settings
        from fairy.runner.main import check_port
        from fairy.paths import DRAFT_MODEL, PROMPT, SERVER
        try:
            check_environment()
            check_llama()
            brain_port, brain, _, _ = brain_settings()
            port = int(os.getenv("FAIRY_DESKTOP_OMNI_PORT", "8080"))
            omni_port, omni, projector, _, _ = omni_settings(port)
            if omni_port != port or brain_port == port:
                raise ValueError("Model ports must be different and match their configured URLs")
            check_port(port)
            check_port(brain_port)
            for file in (brain, omni, projector, DRAFT_MODEL, PROMPT, SERVER):
                if not file.is_file():
                    raise RuntimeError(f"Missing file: {file}")
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            print(f"[ERROR] {error}", file=sys.stderr)
            return 1
        print("[PASS] Desktop prerequisites and model files found; models were not started.")
        return 0
    environment = os.environ.copy()
    environment["PATH"] = str(Path(npm).parent) + os.pathsep + environment.get("PATH", "")
    try:
        return subprocess.call([npm, "start"], cwd=ROOT / "desktop", env=environment)
    except (OSError, KeyboardInterrupt) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

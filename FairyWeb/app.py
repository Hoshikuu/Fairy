"""Start the local FairyWeb llama.cpp server without extra Python packages."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "llama" / "llama-server.exe"
MODEL = ROOT / "LFM3-Omni-2B-Q8_0.gguf"
PROJECTOR = ROOT / "mmproj-LFM3-Omni-2B-Q8_0.gguf"
PUBLIC = ROOT / "public"


def port_number(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("El puerto debe estar entre 1 y 65535.")
    return port


def main() -> int:
    parser = argparse.ArgumentParser(description="Inicia FairyWeb con llama.cpp local.")
    parser.add_argument("--port", type=port_number, default=8090, help="Puerto local (por defecto: 8090).")
    parser.add_argument("--check", action="store_true", help="Comprueba los archivos sin iniciar el modelo.")
    args = parser.parse_args()

    missing = [path for path in (SERVER, MODEL, PROJECTOR, PUBLIC / "index.html") if not path.is_file()]
    if missing:
        for path in missing:
            print(f"Falta: {path}", file=sys.stderr)
        return 1
    if args.check:
        print("Archivos de FairyWeb encontrados. No se ha iniciado el modelo.")
        return 0

    command = [
        str(SERVER), "-m", str(MODEL), "--mmproj", str(PROJECTOR),
        "--reasoning", "off", "--temp", "0", "--host", "127.0.0.1",
        "--port", str(args.port), "--path", str(PUBLIC), "--cors-origins", "localhost",
        "-ngl", "99", "-c", "4096",
    ]
    print(f"Cargando el modelo. Abre http://127.0.0.1:{args.port} cuando esté listo.", flush=True)
    print("Pulsa Ctrl+C para detener el servidor.", flush=True)
    try:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL)
    except OSError as error:
        print(f"No se pudo iniciar llama-server: {error}", file=sys.stderr)
        return 1
    try:
        return process.wait()
    except KeyboardInterrupt:
        print("\nDeteniendo llama-server...", flush=True)
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 0


if __name__ == "__main__":
    sys.exit(main())

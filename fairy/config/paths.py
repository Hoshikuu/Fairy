"""Project paths independent of the working directory."""
from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
PROMPT_FILE = PROJECT_ROOT / "prompt" / "system.txt"
LLAMA_DIR = PROJECT_ROOT / "llama"
WHISPER_DIR = PROJECT_ROOT / "whisper"
LLAMA_SERVER = LLAMA_DIR / "llama-server.exe"
WHISPER_SERVER = WHISPER_DIR / "Release" / "whisper-server.exe"
LLAMA_MODEL = MODELS_DIR / "Spark-X2.5-4B-Q4_K_M.gguf"
WHISPER_MODEL = MODELS_DIR / "ggml-small.bin"
KOKORO_ENV = PROJECT_ROOT / ".venv-kokoro"
KOKORO_PYTHON = KOKORO_ENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
BOT_ENV = PROJECT_ROOT / ".venv"
BOT_PYTHON = BOT_ENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

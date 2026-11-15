from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAIRY = ROOT / "fairy"
MODELS = ROOT / "models"
BRAIN_MODEL = MODELS / "MiniCPM5-2B-Q4_K_M.gguf"
SERVER = ROOT / "llama" / "llama-server.exe"
OMNI_MODEL = MODELS / "LFM3-Omni-2B-Q4_K_M.gguf"
OMNI_PROJECTOR = MODELS / "mmproj-LFM3-Omni-2B-Q4_K_M.gguf"
DRAFT_SOURCE = MODELS / "MiniCPM5-2.6B-DSpark.gguf"
DRAFT_MODEL = MODELS / "MiniCPM5-2.6B-DSpark-Q4_K_M.gguf"
QUANTIZE = ROOT / "llama" / "llama-quantize.exe"
PROMPT = FAIRY / "prompts" / "system.txt"
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"

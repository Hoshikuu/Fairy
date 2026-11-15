import os
from pathlib import Path


def _asset_root(root: Path) -> Path:
    configured = os.getenv("FAIRY_ASSET_ROOT", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    git_file = root / ".git"
    if git_file.is_file():
        for line in git_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("gitdir:"):
                raw = line.split(":", 1)[1].strip()
                if raw:
                    gitdir_path = Path(raw)
                    if not gitdir_path.is_absolute():
                        gitdir_path = (root / gitdir_path).resolve()
                    else:
                        gitdir_path = gitdir_path.resolve()
                    candidate = gitdir_path.parent.parent.parent
                    if candidate.is_dir():
                        return candidate
                break
    return root


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = _asset_root(ROOT)


def _pick(*parts: str) -> Path:
    local = ROOT.joinpath(*parts)
    return local if local.exists() else ASSET_ROOT.joinpath(*parts)


FAIRY = ROOT / "fairy"
MODELS = _pick("models")
BRAIN_MODEL = MODELS / "MiniCPM5-2B-Q4_K_M.gguf"
SERVER = _pick("llama", "llama-server.exe")
OMNI_MODEL = MODELS / "LFM3-Omni-2B-Q4_K_M.gguf"
OMNI_PROJECTOR = MODELS / "mmproj-LFM3-Omni-2B-Q4_K_M.gguf"
DRAFT_SOURCE = MODELS / "MiniCPM5-2.6B-DSpark.gguf"
DRAFT_MODEL = MODELS / "MiniCPM5-2.6B-DSpark-Q4_K_M.gguf"
QUANTIZE = _pick("llama", "llama-quantize.exe")
PROMPT = FAIRY / "prompts" / "system.txt"
VENV_PYTHON = _pick(".venv", "Scripts", "python.exe")
ELECTRON_EXE = _pick("desktop", "node_modules", "electron", "dist", "electron.exe")

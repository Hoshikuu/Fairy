"""Offline Python/dependency probes and setup-time environment preparation."""
from pathlib import Path
import subprocess
import sys
from fairy.config.paths import PROJECT_ROOT


def run_python(python: Path, arguments, *, capture=False, timeout=120, interactive=False):
    return subprocess.run([str(python), *arguments], cwd=PROJECT_ROOT, check=True,
                          stdin=None if interactive else subprocess.DEVNULL,
                          capture_output=capture, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


def require_python(python: Path):
    if not python.is_file():
        raise RuntimeError(f"Python is missing: {python}. Run python setup.py.")
    try:
        run_python(python, ["-c", "import sys; assert (3,11) <= sys.version_info[:2] < (3,13), 'Python 3.11-3.12 required for asyncio.timeout and Kokoro 0.9.4'"],
                   capture=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        detail = getattr(error, "stderr", None) or getattr(error, "stdout", None) or str(error)
        raise RuntimeError(f"Python environment is unusable: {python}. Run python setup.py.\n{detail}") from error


def require_dependencies(python: Path, kind="bot"):
    require_python(python)
    modules = ("import discord, davey, nacl, httpx, openai, dotenv, requests, tqdm, huggingface_hub, packaging; "
               "from discord.ext import voice_recv; "
               "assert hasattr(voice_recv.VoiceRecvClient, 'stop_playing')") if kind == "bot" else (
               "import kokoro, misaki, fastapi, uvicorn, soundfile, torch, en_core_web_sm")
    try:
        run_python(python, ["-c", modules], capture=True, timeout=60)
        run_python(python, ["-m", "pip", "check"], capture=True, timeout=30)
        requirements = PROJECT_ROOT / ("requirements.txt" if kind == "bot" else "requirements-kokoro.txt")
        code = """
from importlib.metadata import distribution
from packaging.requirements import Requirement
from pathlib import Path
import json, sys
for line in Path(sys.argv[1]).read_text(encoding='utf-8').splitlines():
    if not line.strip() or line.lstrip().startswith('#'):
        continue
    requirement = Requirement(line)
    if requirement.marker and not requirement.marker.evaluate():
        continue
    installed = distribution(requirement.name)
    assert installed.version in requirement.specifier, f'{requirement.name}: {installed.version} violates {requirement.specifier}'
    if requirement.url and requirement.url.startswith('git+'):
        revision = requirement.url.rsplit('@', 1)[-1]
        direct = json.loads(installed.read_text('direct_url.json') or '{}')
        assert direct.get('vcs_info', {}).get('commit_id') == revision, f'{requirement.name}: pinned Git revision missing'
"""
        run_python(python, ["-c", code, str(requirements)], capture=True, timeout=30)
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"{kind} dependencies are invalid. Run python setup.py --only {kind}.\n"
                           + (error.stderr or error.stdout or "")[-2000:]) from error


def prepare_bot_environment(python: Path):
    # Upgrade a stale venv in place; do not delete unrelated installed files.
    try:
        require_python(python)
    except RuntimeError:
        expected = PROJECT_ROOT / ".venv"
        if python.resolve().parent.parent != expected.resolve():
            raise RuntimeError("Use an existing Python for --bot-python; automatic creation is limited to .venv")
        run_python(Path(sys.executable), ["-m", "venv", "--upgrade" if python.exists() else "--copies",
                                         str(expected)], timeout=120)
    run_python(python, ["-m", "pip", "install", "-r", str(PROJECT_ROOT / "requirements.txt")], timeout=600)
    require_dependencies(python, "bot")

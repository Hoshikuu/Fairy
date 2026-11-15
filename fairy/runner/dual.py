"""Manage the two local llama.cpp inference services."""

import asyncio
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit

from fairy.ai.brain import BrainConfig
from fairy.paths import BRAIN_MODEL, DRAFT_MODEL, OMNI_MODEL, OMNI_PROJECTOR, SERVER
from fairy.runner.main import check_port, stop_llama, wait_ready


def use_draft() -> bool:
    return os.getenv("FAIRY_USE_DRAFT", "0").strip().lower() in ("1", "true", "yes", "on")


def omni_settings(port: int = 8080) -> tuple[int, Path, Path, int, int]:
    parts = urlsplit(os.getenv("FAIRY_OMNI_URL", f"http://127.0.0.1:{port}"))
    if (parts.scheme != "http" or parts.hostname not in ("127.0.0.1", "localhost")
            or parts.username or parts.password or parts.path not in ("", "/")
            or parts.query or parts.fragment):
        raise ValueError("FAIRY_OMNI_URL must be a local HTTP origin")
    port = parts.port or 80
    model = Path(os.getenv("FAIRY_OMNI_MODEL_PATH", str(OMNI_MODEL)))
    projector = Path(os.getenv("FAIRY_OMNI_PROJECTOR_PATH", str(OMNI_PROJECTOR)))
    context = int(os.getenv("FAIRY_OMNI_CONTEXT", "2048"))
    layers = int(os.getenv("FAIRY_OMNI_GPU_LAYERS", "99"))
    if not 1 <= port <= 65535 or context < 512 or layers < 0:
        raise ValueError("Invalid LFM3 server configuration")
    return port, model, projector, context, layers


def brain_settings() -> tuple[int, Path, int, int]:
    config = BrainConfig.from_env()
    parts = urlsplit(config.url)
    port = parts.port or 80
    model = Path(os.getenv("FAIRY_BRAIN_MODEL_PATH", str(BRAIN_MODEL)))
    layers = int(os.getenv("FAIRY_BRAIN_GPU_LAYERS", "20"))
    if not 1 <= port <= 65535 or layers < 0:
        raise ValueError("Invalid MiniCPM server configuration")
    return port, model, config.context, layers


async def start_brain(timeout: float) -> subprocess.Popen:
    port, model, context, layers = brain_settings()
    draft_enabled = use_draft()
    draft = Path(os.getenv("FAIRY_DRAFT_MODEL_PATH", str(DRAFT_MODEL)))
    required = [SERVER, model]
    if draft_enabled:
        required.append(draft)
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"Missing MiniCPM component: {path}")
    check_port(port)
    command = [str(SERVER), "-m", str(model.resolve()), "--jinja", "--host", "127.0.0.1",
               "--port", str(port), "-ngl", str(layers), "-c", str(context), "--cors-origins", "localhost",
               "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0"]
    if draft_enabled:
        command.extend(["-md", str(draft.resolve()), "--spec-type", "draft-dspark",
                        "--spec-draft-n-max", "7", "-ngld", str(layers)])
    print(f"[STRT]  Starting MiniCPM on port {port}; GPU layers: {layers}", flush=True)
    process = subprocess.Popen(command, cwd=SERVER.parent, stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr)
    try:
        await wait_ready(process, port, timeout, name="MiniCPM")
    except BaseException:
        await stop_llama(process)
        raise
    return process


async def start_omni(timeout: float, port: int = 8080) -> subprocess.Popen:
    configured_port, model, projector, context, layers = omni_settings(port)
    if configured_port != port:
        raise ValueError("FAIRY_OMNI_URL port must match --port")
    for path in (SERVER, model, projector):
        if not path.is_file():
            raise RuntimeError(f"Missing LFM3 component: {path}")
    # Never take over or stop a pre-existing listener whose identity is unknown.
    check_port(port)
    command = [str(SERVER), "-m", str(model.resolve()), "--mmproj", str(projector.resolve()),
               "--jinja", "--host", "127.0.0.1", "--port", str(port), "-ngl", str(layers),
               "-c", str(context), "--reasoning", "off", "--cors-origins", "localhost",
               "-fa", "on", "-ctk", "q8_0", "-ctv", "q8_0"]
    print(f"[STRT]  Starting LFM3 on port {port}; GPU layers: {layers}", flush=True)
    process = subprocess.Popen(command, cwd=SERVER.parent, stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr)
    try:
        await wait_ready(process, port, timeout, name="LFM3")
    except BaseException:
        await stop_llama(process)
        raise
    return process

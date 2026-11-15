import asyncio
import json
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener



def check_port(port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(f"Port {port} is unavailable") from error


async def wait_ready(process: subprocess.Popen, port: int, timeout: float = 360, *, name: str = "LFM3") -> None:
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout

    def probe() -> bool:
        try:
            with opener.open(f"http://127.0.0.1:{port}/health", timeout=2) as response:
                return response.status == 200 and json.load(response).get("status") == "ok"
        except (OSError, URLError, ValueError):
            return False

    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"llama-server exited with code {process.returncode}")
        if await asyncio.to_thread(probe):
            print(f"[PASS]  {name} is ready", flush=True)
            return
        await asyncio.sleep(0.5)
    raise TimeoutError("llama-server did not become ready")


async def stop_llama(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=10)
    except TimeoutError:
        process.kill()
        await asyncio.to_thread(process.wait)
    print("[STOP]  llama-server stopped", flush=True)

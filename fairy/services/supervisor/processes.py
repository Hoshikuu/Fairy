"""Launch, continuously drain, probe and stop subprocesses."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from fairy.config.paths import PROJECT_ROOT


def log_output(name: str, process: subprocess.Popen[str]) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        print(f"[{name}] {line}", end="", flush=True)


def launch(name: str, command: list[str], children: dict[str, subprocess.Popen[str]]) -> None:
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=flags,
    )
    children[name] = process
    threading.Thread(target=log_output, args=(name, process), daemon=True).start()
    print(f"{name} started (PID {process.pid})", flush=True)


def wait_ready(
    name: str,
    host: str,
    port: int,
    children: dict[str, subprocess.Popen[str]],
    timeout: float,
    stop_event=None,
) -> None:
    probe_host = "127.0.0.1" if host == "0.0.0.0" else host
    url = f"http://{probe_host}:{port}/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stop_event is not None and stop_event.is_set():
            raise InterruptedError("Service startup was cancelled")
        for child_name, process in children.items():
            if process.poll() is not None:
                raise RuntimeError(f"{child_name} exited with code {process.returncode}")
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    print(f"{name} ready: {url}", flush=True)
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"{name} did not become ready within {timeout:.0f} seconds")


def stop_children(children: dict[str, subprocess.Popen[str]]) -> None:
    active = [process for process in children.values() if process.poll() is None]
    for process in active:
        try:
            if os.name == "nt":
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                process.terminate()
        except OSError:
            process.terminate()

    for process in active:
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def listen_for_quit(stop_event: threading.Event) -> None:
    if sys.stdin is None:
        return
    while not stop_event.is_set():
        line = sys.stdin.readline()
        if not line:
            return
        if line.strip().lower() == "q":
            stop_event.set()
            return

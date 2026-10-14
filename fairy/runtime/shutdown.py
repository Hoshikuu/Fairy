"""Signal handling and bounded shutdown of processes owned by Fairy."""
import os
import signal
import subprocess


def install_stop_handlers(stop_event):
    previous = {}
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        value = getattr(signal, name, None)
        if value is not None:
            previous[value] = signal.getsignal(value)
            signal.signal(value, lambda signum, frame: stop_event.set())
    return previous


def restore_handlers(previous):
    for signum, handler in previous.items():
        signal.signal(signum, handler)


def stop_process(process, *, stdin_quit=False, timeout=12):
    if process is None or process.poll() is not None:
        return
    try:
        if stdin_quit and process.stdin is not None:
            process.stdin.write("q\n")
            process.stdin.flush()
            process.stdin.close()
        elif os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            process.terminate()
    except (OSError, ValueError):
        if process.poll() is None:
            process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        if process.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=10)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)

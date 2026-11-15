import sys
import time


def size_text(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024


class Progress:
    def __init__(self, label: str, total: int | None):
        self.label = label
        self.total = total if total and total > 0 else None
        self.current = 0
        self.last_update = 0.0
        self.terminal = sys.stdout.isatty()
        if self.terminal:
            self.update(0, force=True)

    def update(self, amount: int, *, force: bool = False) -> None:
        self.current = amount
        now = time.monotonic()
        if not self.terminal or (not force and now - self.last_update < 0.1):
            return
        self.last_update = now
        if self.total:
            fraction = min(amount / self.total, 1.0)
            filled = int(fraction * 30)
            bar = "/" * filled + " " * (30 - filled)
            status = f"[{bar}] {fraction * 100:5.1f}%  {size_text(amount)} / {size_text(self.total)}"
        else:
            status = size_text(amount)
        print(f"\r[INFO]  {self.label}: {status}   ", end="", flush=True)

    def finish(self) -> None:
        if self.terminal:
            self.update(self.current, force=True)
            print(flush=True)
        else:
            print(f"[INFO]  {self.label}: {size_text(self.current)}", flush=True)

    def abort(self) -> None:
        if self.terminal:
            print(flush=True)

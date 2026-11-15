"""Local assistant tools for time, windows, system stats, clipboard, and memory."""

import asyncio
import ctypes
from ctypes import wintypes
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable

from fairy.ai.brain import Tool
from fairy.paths import ROOT

_MAX_MEMORY_ENTRIES = 100
_MAX_KEY_LEN = 80
_MAX_FACT_LEN = 300
_MAX_WINDOWS = 15
_MAX_CLIPBOARD_CHARS = 2000
_CF_UNICODETEXT = 13


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


def _window_title(user32: object, hwnd: int) -> str:
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    copied = user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value[:copied].strip() if copied > 0 else ""


def _read_windows_info() -> dict[str, object]:
    if sys.platform != "win32":
        return {"active_window": "", "open_windows": [], "note": "Window inspection is only available on Windows."}
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    wndenumproc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [wndenumproc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL

    active = _window_title(user32, user32.GetForegroundWindow())
    titles: list[str] = []
    seen: set[str] = set()

    def _collect(hwnd: int, _lparam: int) -> bool:
        if user32.IsWindowVisible(hwnd):
            title = _window_title(user32, hwnd)
            if title and title not in seen:
                seen.add(title)
                titles.append(title)
                if len(titles) >= _MAX_WINDOWS:
                    return False
        return True

    callback = wndenumproc(_collect)
    user32.EnumWindows(callback, 0)
    return {"active_window": active, "open_windows": titles}


def _read_ram_stats() -> dict[str, float | int] | None:
    if sys.platform != "win32":
        return None
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MEMORYSTATUSEX)]
    kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
    status = _MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    total_gb = status.ullTotalPhys / (1024 ** 3)
    avail_gb = status.ullAvailPhys / (1024 ** 3)
    return {
        "ram_total_gb": round(total_gb, 2),
        "ram_used_gb": round(total_gb - avail_gb, 2),
        "ram_percent": int(status.dwMemoryLoad),
    }


def _query_gpu_stats() -> dict[str, int] | None:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    result = subprocess.run(
        [exe, "--query-gpu=memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        timeout=2.0,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    line = result.stdout.strip().splitlines()[0]
    parts = [part.strip() for part in line.split(",")]
    if len(parts) != 3:
        return None
    return {
        "vram_used_mb": int(float(parts[0])),
        "vram_total_mb": int(float(parts[1])),
        "gpu_utilization_percent": int(float(parts[2])),
    }


def _read_clipboard_text() -> str:
    if sys.platform != "win32":
        return "Clipboard reading is only available on Windows."
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = wintypes.BOOL
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    if not user32.OpenClipboard(None):
        return "Could not open clipboard."
    try:
        if not user32.IsClipboardFormatAvailable(_CF_UNICODETEXT):
            return "Clipboard is empty or has no text."
        handle = user32.GetClipboardData(_CF_UNICODETEXT)
        if not handle:
            return "Clipboard is empty or has no text."
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return "Clipboard is empty or has no text."
        try:
            text = ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()
    if not text:
        return "Clipboard is empty or has no text."
    return text[:_MAX_CLIPBOARD_CHARS]


def _load_memory(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def assistant_tools(
    memory_path: Path | None = None,
    notify: Callable[[str], None] | None = None,
) -> dict[str, Tool]:
    """Return local assistant tools for time, windows, system stats, clipboard, and memory."""
    storage = memory_path or (ROOT / ".fairy_memory.json")

    async def get_current_time(_arguments: dict) -> str:
        now = datetime.now().astimezone()
        return json.dumps(
            {
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "weekday": now.strftime("%A"),
                "iso": now.isoformat(timespec="seconds"),
            },
            ensure_ascii=False,
        )

    async def get_active_windows(_arguments: dict) -> str:
        return json.dumps(_read_windows_info(), ensure_ascii=False)

    async def get_system_stats(_arguments: dict) -> str:
        disk = shutil.disk_usage(ROOT)
        stats: dict[str, object] = {
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_free_gb": round(disk.free / (1024 ** 3), 2),
        }
        ram = _read_ram_stats()
        if ram is not None:
            stats.update(ram)
        try:
            gpu = await asyncio.to_thread(_query_gpu_stats)
        except Exception:
            gpu = None
        if gpu is not None:
            stats.update(gpu)
        return json.dumps(stats, ensure_ascii=False)

    async def read_clipboard(_arguments: dict) -> str:
        return _read_clipboard_text()

    async def remember_fact(arguments: dict) -> str:
        key = arguments["key"].strip()
        fact = arguments["fact"].strip()
        if not key or len(key) > _MAX_KEY_LEN:
            raise ValueError("Memory key must be 1 to 80 characters")
        if not fact or len(fact) > _MAX_FACT_LEN:
            raise ValueError("Memory fact must be 1 to 300 characters")
        data = _load_memory(storage)
        while key not in data and len(data) >= _MAX_MEMORY_ENTRIES:
            oldest = next(iter(data))
            del data[oldest]
        data[key] = fact
        storage.parent.mkdir(parents=True, exist_ok=True)
        storage.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if notify:
            notify(f"Remembered: {key}")
        return f"Saved fact for {key}."

    async def recall_facts(_arguments: dict) -> str:
        data = _load_memory(storage)
        if not data:
            return "No saved facts yet."
        return json.dumps(data, ensure_ascii=False)

    empty_schema = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
    return {
        "get_current_time": Tool(
            "get_current_time",
            "Get the current local date, time, weekday, and ISO timestamp.",
            empty_schema,
            get_current_time,
        ),
        "get_active_windows": Tool(
            "get_active_windows",
            "Get the active foreground window title and up to 15 open visible window titles.",
            empty_schema,
            get_active_windows,
        ),
        "get_system_stats": Tool(
            "get_system_stats",
            "Get current RAM, disk usage, and GPU VRAM statistics when available.",
            empty_schema,
            get_system_stats,
        ),
        "read_clipboard": Tool(
            "read_clipboard",
            "Read current plain text from the Windows clipboard.",
            empty_schema,
            read_clipboard,
        ),
        "remember_fact": Tool(
            "remember_fact",
            "Save a short personal fact or preference under a label for later recall.",
            {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Short label for the fact (max 80 chars)."},
                    "fact": {"type": "string", "description": "Fact text to save (max 300 chars)."},
                },
                "required": ["key", "fact"],
                "additionalProperties": False,
            },
            remember_fact,
        ),
        "recall_facts": Tool(
            "recall_facts",
            "Recall all previously saved user facts and preferences.",
            empty_schema,
            recall_facts,
        ),
    }

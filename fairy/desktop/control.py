"""Small, explicitly enabled set of Windows desktop actions."""

import ctypes
import sys

from fairy.ai.brain import Tool


def desktop_tools(enabled, notify) -> dict[str, Tool]:
    async def click(arguments: dict) -> str:
        if not enabled() or sys.platform != "win32":
            return "Desktop control is disabled or unavailable."
        x, y = arguments["x"], arguments["y"]
        user = ctypes.windll.user32
        left, top = user.GetSystemMetrics(76), user.GetSystemMetrics(77)
        width, height = user.GetSystemMetrics(78), user.GetSystemMetrics(79)
        if not left <= x < left + width or not top <= y < top + height:
            raise ValueError("Coordinates are outside the desktop")
        notify(f"Click at {x}, {y}")
        if not user.SetCursorPos(x, y):
            raise OSError("Could not move pointer")
        user.mouse_event(2, 0, 0, 0, 0)
        user.mouse_event(4, 0, 0, 0, 0)
        return "Clicked."

    async def press(arguments: dict) -> str:
        if not enabled() or sys.platform != "win32":
            return "Desktop control is disabled or unavailable."
        key = arguments["key"]
        keys = {"enter": 0x0D, "escape": 0x1B, "tab": 0x09, "space": 0x20,
                "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
                "backspace": 0x08}
        if key not in keys:
            raise ValueError("Unsupported key")
        notify(f"Press {key}")
        user = ctypes.windll.user32
        user.keybd_event(keys[key], 0, 0, 0)
        user.keybd_event(keys[key], 0, 2, 0)
        return "Key pressed."

    return {
        "desktop_click": Tool("desktop_click", "Click an absolute Windows desktop coordinate when requested. Coordinates are physical screen pixels.",
            {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
             "required": ["x", "y"], "additionalProperties": False}, click),
        "desktop_key": Tool("desktop_key", "Press a navigation key on the desktop when requested.",
            {"type": "object", "properties": {"key": {"type": "string", "enum": ["enter", "escape", "tab", "space", "up", "down", "left", "right", "backspace"]}},
             "required": ["key"], "additionalProperties": False}, press),
    }

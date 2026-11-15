"""Small, explicitly enabled set of Windows desktop actions."""

import ctypes
import sys
from ctypes import wintypes

from fairy.ai.brain import Tool

DISABLED = "Desktop control is disabled or unavailable."
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
VK_RETURN = 0x0D
MAX_TYPED_CHARACTERS = 200
MAX_SCROLL_CLICKS = 20
MEDIA_KEYS = {
    "play_pause": 0xB3,
    "next_track": 0xB0,
    "prev_track": 0xB1,
    "volume_up": 0xAF,
    "volume_down": 0xAE,
    "volume_mute": 0xAD,
}


class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", wintypes.WPARAM)]


class KeyboardInput(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", wintypes.WPARAM)]


class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class InputUnion(ctypes.Union):
    _fields_ = [("mi", MouseInput), ("ki", KeyboardInput), ("hi", HardwareInput)]


class Input(ctypes.Structure):
    """Windows INPUT record; the union keeps the native 40-byte size on x64."""

    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", InputUnion)]


def _user32():
    """Return user32 with physical-pixel metrics and explicit signatures."""
    user = ctypes.windll.user32
    try:
        user.SetProcessDPIAware()
    except Exception:
        pass
    try:
        user.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(Input), ctypes.c_int]
        user.SendInput.restype = wintypes.UINT
    except Exception:
        pass
    return user


def _unicode_events(text: str) -> list[Input]:
    events = []
    for character in text:
        virtual_key, scan, flags = (VK_RETURN, 0, 0) if character == "\n" else (0, ord(character), KEYEVENTF_UNICODE)
        for extra in (0, KEYEVENTF_KEYUP):
            record = Input(type=INPUT_KEYBOARD)
            record.ki = KeyboardInput(virtual_key, scan, flags | extra, 0, 0)
            events.append(record)
    return events


def _validate_text(text) -> str:
    if not isinstance(text, str) or not 0 < len(text) <= MAX_TYPED_CHARACTERS:
        raise ValueError(f"Text must contain 1 to {MAX_TYPED_CHARACTERS} characters")
    for character in text:
        if character != "\n" and (not character.isprintable() or ord(character) > 0xFFFF):
            raise ValueError("Text contains unsupported characters")
    return text


def desktop_tools(enabled, notify) -> dict[str, Tool]:
    async def click(arguments: dict) -> str:
        if not enabled() or sys.platform != "win32":
            return DISABLED
        x, y = arguments["x"], arguments["y"]
        screen_width, screen_height = arguments.get("screen_width"), arguments.get("screen_height")
        user = _user32()
        left, top = user.GetSystemMetrics(76), user.GetSystemMetrics(77)
        width, height = user.GetSystemMetrics(78), user.GetSystemMetrics(79)
        for size in (screen_width, screen_height):
            if size is not None and (isinstance(size, bool) or not isinstance(size, int) or size <= 0):
                raise ValueError("Screen size must be a positive integer")
        if screen_width is not None:
            x = left + round(x * width / screen_width)
        if screen_height is not None:
            y = top + round(y * height / screen_height)
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
            return DISABLED
        key = arguments["key"]
        keys = {"enter": 0x0D, "escape": 0x1B, "tab": 0x09, "space": 0x20,
                "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
                "backspace": 0x08}
        if key not in keys:
            raise ValueError("Unsupported key")
        notify(f"Press {key}")
        user = _user32()
        user.keybd_event(keys[key], 0, 0, 0)
        user.keybd_event(keys[key], 0, 2, 0)
        return "Key pressed."

    async def type_text(arguments: dict) -> str:
        if not enabled() or sys.platform != "win32":
            return DISABLED
        text = _validate_text(arguments.get("text"))
        events = _unicode_events(text)
        notify(f"Type {len(text)} characters")
        user = _user32()
        array = (Input * len(events))(*events)
        if user.SendInput(len(events), array, ctypes.sizeof(Input)) != len(events):
            raise OSError("Could not type text")
        return "Typed."

    async def scroll(arguments: dict) -> str:
        if not enabled() or sys.platform != "win32":
            return DISABLED
        clicks = arguments.get("clicks")
        if isinstance(clicks, bool) or not isinstance(clicks, int) or not -MAX_SCROLL_CLICKS <= clicks <= MAX_SCROLL_CLICKS:
            raise ValueError(f"Clicks must be an integer from -{MAX_SCROLL_CLICKS} to {MAX_SCROLL_CLICKS}")
        notify(f"Scroll {clicks}")
        user = _user32()
        # The wheel delta is a signed value carried in an unsigned DWORD.
        user.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, ctypes.c_uint32(clicks * 120).value, 0)
        return "Scrolled."

    async def media(arguments: dict) -> str:
        if not enabled() or sys.platform != "win32":
            return DISABLED
        action = arguments.get("action")
        if action not in MEDIA_KEYS:
            raise ValueError("Unsupported media action")
        notify(f"Media {action}")
        user = _user32()
        user.keybd_event(MEDIA_KEYS[action], 0, KEYEVENTF_EXTENDEDKEY, 0)
        user.keybd_event(MEDIA_KEYS[action], 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        return "Media key pressed."

    return {
        "desktop_click": Tool("desktop_click", "Click an absolute Windows desktop coordinate when requested. Coordinates are physical screen pixels, or pixels of a scaled screen capture when screen_width and screen_height are given.",
            {"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"},
                                              "screen_width": {"type": "integer"},
                                              "screen_height": {"type": "integer"}},
             "required": ["x", "y"], "additionalProperties": False}, click),
        "desktop_key": Tool("desktop_key", "Press a navigation key on the desktop when requested.",
            {"type": "object", "properties": {"key": {"type": "string", "enum": ["enter", "escape", "tab", "space", "up", "down", "left", "right", "backspace"]}},
             "required": ["key"], "additionalProperties": False}, press),
        "desktop_type": Tool("desktop_type", "Type short plain text into the focused desktop window when requested.",
            {"type": "object", "properties": {"text": {"type": "string", "description": "Plain text, 1 to 200 characters."}},
             "required": ["text"], "additionalProperties": False}, type_text),
        "desktop_scroll": Tool("desktop_scroll", "Scroll the window under the pointer vertically; positive clicks scroll up, negative scroll down.",
            {"type": "object", "properties": {"clicks": {"type": "integer", "description": "Whole clicks from -20 to 20."}},
             "required": ["clicks"], "additionalProperties": False}, scroll),
        "media_control": Tool("media_control", "Send a media or volume key when requested.",
            {"type": "object", "properties": {"action": {"type": "string", "enum": list(MEDIA_KEYS)}},
             "required": ["action"], "additionalProperties": False}, media),
    }

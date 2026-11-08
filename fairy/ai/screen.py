"""A read-only screen tool bound to one conversation's frame provider."""

import base64
import json
from typing import Callable

from fairy.ai.brain import Tool
from fairy.realtime.omni import OmniClient

SCREEN_TOOL_INSTRUCTIONS = (
    "\nThis user is currently sharing a screen. You have access through the view_screen tool. "
    "When the user asks about their screen, call view_screen before answering. "
    "Do not claim that you cannot access the screen while this tool is available. "
    "An ASR transcript represents the user's request, although recognition can be inaccurate.")


def screen_tool(omni: OmniClient, frame_provider: Callable[[], str | None]) -> Tool:
    async def view_screen(arguments: dict) -> str:
        question = arguments["question"]
        if not question.strip() or len(question) > 2000:
            raise ValueError("Screen analysis requires a question under 2000 characters")
        encoded = frame_provider()
        if not encoded:
            return "The shared screen is no longer available. Ask the user to share it again."
        image = base64.b64decode(encoded, validate=True)
        observation = await omni.describe([(image, "image/jpeg")], question)
        return json.dumps({"source": "LFM3 analysis of this user's shared screen",
                           "observation": observation}, ensure_ascii=False)

    return Tool(
        "view_screen", "Inspect the user's currently shared screen when they ask about it. "
        "Provide the specific visual question. Treat the analysis as an observation from another model.",
        {"type": "object", "properties": {"question": {"type": "string"}},
         "required": ["question"], "additionalProperties": False}, view_screen, timeout=180)

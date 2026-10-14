"""Split generated answers into speech-sized phrases."""

from __future__ import annotations

import re


def speech_chunks(text: str):
    """Split long LLM answers at sentence boundaries to fit the service limit."""
    remaining = text.strip()
    while remaining:
        end = min(len(remaining), 1000)
        if end < len(remaining):
            boundaries = list(re.finditer(r"[.!?]\s+|\n+", remaining[:end]))
            boundary = boundaries[-1].end() if boundaries else remaining.rfind(" ", 0, end)
            if boundary > 0:
                end = boundary
        chunk, remaining = remaining[:end].strip(), remaining[end:].lstrip()
        if chunk:
            yield chunk

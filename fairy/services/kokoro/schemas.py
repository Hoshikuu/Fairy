"""Validated OpenAI-style speech request."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SpeechRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: Literal["kokoro"] = "kokoro"
    input: str = Field(min_length=1, max_length=4000)
    voice: str | None = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0, allow_inf_nan=False)
    response_format: Literal["wav"] = "wav"

    @field_validator("input")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("input must contain text")
        return value

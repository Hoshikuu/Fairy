"""MiniCPM conversation through llama.cpp's local chat API."""

import asyncio
from dataclasses import dataclass, field
import json
import logging
import os
import re
import time
from typing import Awaitable, Callable
from urllib.parse import urlsplit
from pathlib import Path

from fairy.paths import BRAIN_MODEL

import aiohttp

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BrainConfig:
    url: str = "http://127.0.0.1:8082"
    model: str = "local"
    reasoning: str = "auto"
    context: int = 4096
    max_output: int = 512
    history_turns: int = 12
    temperature: float = 0.7
    timeout: float = 180.0
    max_tool_rounds: int = 3

    def __post_init__(self) -> None:
        parts = urlsplit(self.url)
        if parts.scheme != "http" or parts.hostname not in ("localhost", "127.0.0.1") or parts.username or parts.password or parts.path not in ("", "/") or parts.query or parts.fragment:
            raise ValueError("Brain URL must be a local HTTP origin")
        if self.reasoning not in ("off", "on", "auto"):
            raise ValueError("FAIRY_REASONING_MODE must be off, on or auto")
        if self.context < 512 or self.max_output < 1 or self.history_turns < 1 or self.timeout <= 0 or not 0 <= self.max_tool_rounds <= 10:
            raise ValueError("Invalid brain configuration")

    @classmethod
    def from_env(cls) -> "BrainConfig":
        return cls(
            url=os.getenv("FAIRY_BRAIN_URL", "http://127.0.0.1:8082"),
            model=os.getenv("FAIRY_BRAIN_MODEL", "local"),
            reasoning=os.getenv("FAIRY_REASONING_MODE", "auto").lower(),
            context=int(os.getenv("FAIRY_CONTEXT_SIZE", "4096")),
            max_output=int(os.getenv("FAIRY_BRAIN_MAX_OUTPUT", "512")),
            history_turns=int(os.getenv("FAIRY_HISTORY_TURNS", "12")),
            temperature=float(os.getenv("FAIRY_BRAIN_TEMPERATURE", "0.7")),
            timeout=float(os.getenv("FAIRY_BRAIN_TIMEOUT", "180")),
        )


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[[dict], Awaitable[str]]
    timeout: float = 10.0
    # Tool implementations must authorize the caller before registration or execution.

    def schema(self) -> dict:
        return {"type": "function", "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}


def use_reasoning(mode: str, text: str) -> bool:
    if mode != "auto":
        return mode == "on"
    return bool(re.search(r"\b(code|debug|traceback|math|equation|calculate|algorithm|c[oó]digo|error|calcula|ecuaci[oó]n|demuestra|analiza)\b", text, re.I))


def final_text(content: object) -> str:
    if not isinstance(content, str):
        raise RuntimeError("Brain returned invalid content")
    # Fail closed if inline reasoning markers are malformed.
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.I | re.S)
    if re.search(r"</?think(?:\s|>|$)", content, flags=re.I):
        raise RuntimeError("Brain returned incomplete reasoning markers")
    if re.search(r"</?(?:tool_call|function)(?:\s|>)", content, flags=re.I):
        raise RuntimeError("Brain returned an unparsed tool call")
    if not content.strip():
        raise RuntimeError("Brain returned no final answer")
    return content.strip()


def validate_arguments(parameters: dict, arguments: object) -> dict:
    """Validate a deliberately small JSON-schema subset; reject unsupported schemas."""
    if parameters.get("type") != "object" or not isinstance(arguments, dict):
        raise ValueError("Expected object arguments")
    if set(parameters) - {"type", "properties", "required", "additionalProperties"}:
        raise ValueError("Unsupported tool schema")
    properties = parameters.get("properties", {})
    required = parameters.get("required", [])
    if not isinstance(properties, dict) or not isinstance(required, list):
        raise ValueError("Invalid tool schema")
    if set(arguments) - set(properties) or set(required) - set(arguments):
        raise ValueError("Unknown or missing arguments")
    types = {"string": str, "integer": int, "number": (int, float), "boolean": bool}
    for name, value in arguments.items():
        spec = properties[name]
        if not isinstance(spec, dict) or set(spec) - {"type", "description", "enum"} or spec.get("type") not in types:
            raise ValueError("Unsupported property schema")
        kind = spec["type"]
        if not isinstance(value, types[kind]) or (kind in ("integer", "number") and isinstance(value, bool)):
            raise ValueError("Invalid argument type")
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError("Invalid argument value")
    return arguments


@dataclass
class BrainSession:
    config: BrainConfig
    instructions: str
    tools: dict[str, Tool] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def close(self) -> None:
        # Sessions are request-scoped; no background process is owned here.
        pass

    async def respond_text(self, text: str) -> str:
        async with self.lock:
            model_name = Path(os.getenv("FAIRY_BRAIN_MODEL_PATH", str(BRAIN_MODEL))).name
            print(f"[{model_name}][RECEIVED] {text}", flush=True)
            started = time.monotonic()
            user = {"role": "user", "content": text}
            # A conservative character budget prevents unbounded history without a tokenizer.
            budget = max(512, (self.config.context - self.config.max_output) * 2)
            previous = []
            used = len(self.instructions) + len(text)
            for item in reversed(self.history[-self.config.history_turns * 2:]):
                size = len(json.dumps(item, ensure_ascii=False))
                if used + size > budget:
                    break
                previous.insert(0, item)
                used += size
            if used > budget:
                raise ValueError("Message exceeds the configured conversation budget")
            messages = [{"role": "system", "content": self.instructions}, *previous, user]
            payload = {"model": self.config.model, "messages": messages, "stream": False,
                       "chat_template_kwargs": {"enable_thinking": use_reasoning(self.config.reasoning, text)},
                       "max_tokens": self.config.max_output, "temperature": self.config.temperature}
            if self.tools:
                payload["tools"] = [tool.schema() for tool in self.tools.values()]
            timeout = aiohttp.ClientTimeout(total=self.config.timeout, connect=10)
            async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as client:
                for round_number in range(self.config.max_tool_rounds + 1):
                    print(f"[{model_name}][PROCESSING] Text generation", flush=True)
                    async with client.post(self.config.url.rstrip("/") + "/v1/chat/completions", json=payload) as response:
                        response.raise_for_status()
                        result = await response.json()
                    try:
                        message = result["choices"][0]["message"]
                    except (KeyError, IndexError, TypeError) as error:
                        raise RuntimeError("Brain returned an invalid response") from error
                    if not isinstance(message, dict):
                        raise RuntimeError("Brain returned an invalid response")
                    reasoning = message.get("reasoning_content")
                    if isinstance(reasoning, str) and reasoning.strip():
                        print(f"[{model_name}][REASONING] {reasoning}", flush=True)
                    content = message.get("content")
                    if isinstance(content, str):
                        for inline in re.findall(r"<think>(.*?)</think>", content, flags=re.I | re.S):
                            if inline.strip():
                                print(f"[{model_name}][REASONING] {inline}", flush=True)
                    calls = message.get("tool_calls") or []
                    if not calls:
                        answer = final_text(message.get("content"))
                        print(f"[{model_name}][OUTPUT] {answer}", flush=True)
                        self.history.extend([user, {"role": "assistant", "content": answer}])
                        self.history[:] = self.history[-self.config.history_turns * 2:]
                        log.info("Brain response completed in %.2fs", time.monotonic() - started)
                        return answer
                    if round_number == self.config.max_tool_rounds or not isinstance(calls, list) or len(calls) > 8:
                        raise RuntimeError("Brain exceeded the tool call limit")
                    # Do not preserve or expose the reasoning field.
                    messages.append({"role": "assistant", "content": "", "tool_calls": calls})
                    for call in calls:
                        function = call.get("function", {}) if isinstance(call, dict) else {}
                        name = function.get("name")
                        tool = self.tools.get(name)
                        try:
                            if tool is None:
                                raise ValueError("Tool is not registered")
                            arguments = function.get("arguments")
                            if isinstance(arguments, str):
                                arguments = json.loads(arguments)
                            arguments = validate_arguments(tool.parameters, arguments)
                            output = await asyncio.wait_for(tool.handler(arguments), timeout=tool.timeout)
                            if not isinstance(output, str):
                                raise ValueError("Invalid tool result")
                            output = output[:8000]
                        except (ValueError, TimeoutError):
                            output = "Tool call rejected or timed out."
                        except Exception:
                            log.exception("Tool execution failed")
                            output = "Tool execution failed."
                        messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": output})
            raise RuntimeError("Brain did not produce a final answer")

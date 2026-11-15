"""Local VTube Studio Public API v1.0 client, lip-sync RMS helper, and expression tool."""

import asyncio
import audioop
import logging
import os
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit
import uuid

import aiohttp

from fairy.ai.brain import Tool
from fairy.paths import ROOT

log = logging.getLogger(__name__)

EXPRESSIONS = ("happy", "smug", "flustered", "angry", "surprised", "sad", "neutral")
_NOISE_FLOOR_RMS = 300
_MAX_SPEECH_RMS = 8000


def _validate_ws_url(url: str) -> str:
    parts = urlsplit(url)
    if (
        parts.scheme != "ws"
        or parts.hostname not in ("127.0.0.1", "localhost")
        or parts.username
        or parts.password
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
    ):
        raise ValueError("VTube Studio URL must be a local ws://127.0.0.1 or ws://localhost origin")
    return url


def compute_rms_mouth_open(pcm16_bytes: bytes) -> float:
    """Compute a normalized 0.0..1.0 mouth-open level from 16-bit PCM audio."""
    if len(pcm16_bytes) % 2:
        pcm16_bytes = pcm16_bytes[:-1]
    if not pcm16_bytes:
        return 0.0
    rms = audioop.rms(pcm16_bytes, 2)
    if rms < _NOISE_FLOOR_RMS:
        return 0.0
    level = (rms - _NOISE_FLOOR_RMS) / (_MAX_SPEECH_RMS - _NOISE_FLOOR_RMS)
    return min(1.0, max(0.0, round(level, 3)))


class VTubeClient:
    """Async client for VTube Studio Public API v1.0 on localhost."""

    def __init__(
        self,
        url: str | None = None,
        token_path: Path | None = None,
        plugin_name: str = "Fairy",
        plugin_developer: str = "Fairy",
    ) -> None:
        raw_url = url if url is not None else os.getenv("FAIRY_VTUBE_URL", "ws://127.0.0.1:8001")
        self.url = _validate_ws_url(raw_url)
        self.token_path = token_path or (ROOT / ".vtube_token")
        self.plugin_name = plugin_name
        self.plugin_developer = plugin_developer
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._authenticated = False
        self._lock = asyncio.Lock()

    async def _close_transport(self) -> None:
        self._authenticated = False
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        if self._session is not None:
            try:
                await self._session.close()
            except Exception:
                pass
            self._session = None

    async def close(self) -> None:
        """Close any active WebSocket and HTTP client session."""
        async with self._lock:
            await self._close_transport()

    async def _send_request(self, message_type: str, data: dict | None = None) -> dict:
        if self._ws is None or self._ws.closed:
            raise RuntimeError("VTube Studio WebSocket is not connected")
        request_id = uuid.uuid4().hex
        payload = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": request_id,
            "messageType": message_type,
            "data": data or {},
        }
        await self._ws.send_json(payload)
        while True:
            reply = await self._ws.receive_json(timeout=5.0)
            if not isinstance(reply, dict):
                raise RuntimeError("VTube Studio returned an invalid message")
            if reply.get("requestID") and reply.get("requestID") != request_id:
                continue
            if reply.get("messageType") == "APIError":
                error_data = reply.get("data") or {}
                raise RuntimeError(str(error_data.get("message") or "VTube Studio API error"))
            result = reply.get("data")
            return result if isinstance(result, dict) else {}

    async def _authenticate(self) -> bool:
        token = ""
        if self.token_path.is_file():
            token = self.token_path.read_text(encoding="utf-8").strip()
        if token:
            auth = await self._send_request(
                "AuthenticationRequest",
                {
                    "pluginName": self.plugin_name,
                    "pluginDeveloper": self.plugin_developer,
                    "authenticationToken": token,
                },
            )
            if auth.get("authenticated") is True:
                self._authenticated = True
                return True
        token_reply = await self._send_request(
            "AuthenticationTokenRequest",
            {"pluginName": self.plugin_name, "pluginDeveloper": self.plugin_developer},
        )
        token = str(token_reply.get("authenticationToken") or "").strip()
        if not token:
            return False
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(token, encoding="utf-8")
        auth = await self._send_request(
            "AuthenticationRequest",
            {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_developer,
                "authenticationToken": token,
            },
        )
        self._authenticated = auth.get("authenticated") is True
        return self._authenticated

    async def _ensure_connected(self) -> bool:
        if self._ws is not None and not self._ws.closed and self._authenticated:
            return True
        await self._close_transport()
        timeout = aiohttp.ClientTimeout(total=5.0, connect=2.0)
        self._session = aiohttp.ClientSession(timeout=timeout, trust_env=False)
        try:
            self._ws = await self._session.ws_connect(self.url, timeout=2.0)
            if await self._authenticate():
                return True
        except Exception as error:
            log.debug("VTube Studio connection unavailable: %s", error)
        await self._close_transport()
        return False

    async def connect(self) -> bool:
        """Connect and authenticate with VTube Studio; return False if unavailable."""
        async with self._lock:
            return await self._ensure_connected()

    async def set_mouth_open(self, value: float) -> bool:
        """Inject the MouthOpen parameter value (0.0..1.0) into VTube Studio."""
        clamped = min(1.0, max(0.0, float(value)))
        async with self._lock:
            if not await self._ensure_connected():
                return False
            try:
                await self._send_request(
                    "InjectParameterDataRequest",
                    {"parameterValues": [{"id": "MouthOpen", "value": clamped}], "mode": "set"},
                )
                return True
            except Exception as error:
                log.debug("VTube Studio MouthOpen update failed: %s", error)
                await self._close_transport()
                return False

    async def trigger_hotkey(self, name: str) -> bool:
        """Find a matching hotkey by name in the current model and trigger it."""
        target = name.strip().lower()
        if not target:
            return False
        async with self._lock:
            if not await self._ensure_connected():
                return False
            try:
                data = await self._send_request("HotkeysInCurrentModelRequest")
                hotkeys = data.get("availableHotkeys") or []
                match_id = ""
                for item in hotkeys:
                    if isinstance(item, dict) and str(item.get("name", "")).strip().lower() == target:
                        match_id = str(item.get("hotkeyID") or "")
                        break
                if not match_id:
                    for item in hotkeys:
                        if isinstance(item, dict) and target in str(item.get("name", "")).strip().lower():
                            match_id = str(item.get("hotkeyID") or "")
                            break
                if not match_id:
                    return False
                await self._send_request("HotkeyTriggerRequest", {"hotkeyID": match_id})
                return True
            except Exception as error:
                log.debug("VTube Studio hotkey trigger failed: %s", error)
                await self._close_transport()
                return False

    async def set_expression(self, expression: str) -> str:
        """Trigger a named avatar expression hotkey or return a friendly status message."""
        if expression not in EXPRESSIONS:
            raise ValueError("Unsupported expression")
        if not await self.connect():
            return "VTube Studio is not running or unavailable."
        triggered = await self.trigger_hotkey(expression)
        if not triggered:
            return f"No matching hotkey found for expression '{expression}'."
        return f"Expression set to {expression}."


def vtube_tools(
    client: VTubeClient,
    notify: Callable[[str], None] | None = None,
) -> dict[str, Tool]:
    """Return the VTube Studio expression tool bound to a VTubeClient."""

    async def set_expression(arguments: dict) -> str:
        expression = arguments["expression"]
        if expression not in EXPRESSIONS:
            raise ValueError("Unsupported expression")
        if notify:
            notify(expression)
        return await client.set_expression(expression)

    return {
        "set_expression": Tool(
            "set_expression",
            "Set Fairy's VTube Studio facial expression to match your current mood or reaction.",
            {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Expression name matching the current mood.",
                        "enum": list(EXPRESSIONS),
                    }
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
            set_expression,
        )
    }

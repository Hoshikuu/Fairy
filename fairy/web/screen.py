"""Temporary local screen frames for Discord voice sessions."""

import asyncio
import base64
from dataclasses import dataclass
import time

import aiohttp
from aiohttp import web

MAX_FRAME = 1024 * 1024
MAX_SHARES = 8
FRAME_TTL = 8.0
SCREEN_SHARES = web.AppKey("screen_shares", set)


@dataclass
class ScreenFrame:
    owner: object
    image: str = ""
    updated: float = 0.0


_frames: dict[int, ScreenFrame] = {}


def get_frame(user_id: int) -> str | None:
    """Return a recent JPEG for this Discord ID, if a share is active."""
    frame = _frames.get(user_id)
    if frame is None or not frame.image or time.monotonic() - frame.updated > FRAME_TTL:
        return None
    return frame.image


async def share(request: web.Request) -> web.StreamResponse:
    value = request.query.get("user_id", "")
    if not value.isascii() or not value.isdecimal() or not 15 <= len(value) <= 20:
        raise web.HTTPBadRequest(text="Enter a valid Discord user ID")
    user_id = int(value)
    if user_id in _frames:
        raise web.HTTPConflict(text="This Discord ID is already sharing")
    if len(_frames) >= MAX_SHARES:
        raise web.HTTPServiceUnavailable(text="Too many active screen shares")
    socket = web.WebSocketResponse(max_msg_size=MAX_FRAME, heartbeat=10, receive_timeout=15)
    frame = ScreenFrame(owner=socket)
    _frames[user_id] = frame
    try:
        await socket.prepare(request)
        request.app[SCREEN_SHARES].add(socket)
        async for message in socket:
            if message.type == aiohttp.WSMsgType.BINARY:
                raw = message.data
                if not raw.startswith(b"\xff\xd8\xff") or not raw.endswith(b"\xff\xd9"):
                    await socket.close(code=1003, message=b"Expected JPEG")
                    break
                frame.image = base64.b64encode(raw).decode("ascii")
                frame.updated = time.monotonic()
    finally:
        if _frames.get(user_id) is frame:
            del _frames[user_id]
        request.app[SCREEN_SHARES].discard(socket)
        await socket.close()
    return socket


async def close_shares(app: web.Application) -> None:
    sockets = list(app[SCREEN_SHARES])
    for user_id, frame in list(_frames.items()):
        if frame.owner in sockets:
            del _frames[user_id]
    await asyncio.gather(*(socket.close(code=1001, message=b"Fairy is shutting down") for socket in sockets))
    app[SCREEN_SHARES].clear()


def register_routes(app: web.Application) -> None:
    app[SCREEN_SHARES] = set()
    app.on_shutdown.append(close_shares)
    app.router.add_get("/api/screen", share)

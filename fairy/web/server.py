"""Serve the local information page and temporary screen sharing."""

from pathlib import Path
from urllib.parse import urlsplit

from aiohttp import web

from fairy.web.screen import register_routes

PUBLIC = Path(__file__).resolve().parent / "public"


@web.middleware
async def local_origin(request, handler):
    origin = request.headers.get("Origin")
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in ("http", "https") or parsed.netloc != request.host:
            raise web.HTTPForbidden(text="Origin not allowed")
    response = await handler(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


async def index(request):
    return web.FileResponse(PUBLIC / "index.html")


def create_app():
    app = web.Application(middlewares=[local_origin], client_max_size=1024 * 1024)
    app.router.add_get("/", index)
    app.router.add_static("/assets/", PUBLIC, show_index=False)
    register_routes(app)
    return app

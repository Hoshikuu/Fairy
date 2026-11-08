"""Download and validate a bounded Discord image attachment."""

from urllib.parse import urlsplit

import aiohttp


MAX_IMAGE_BYTES = 8 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
DISCORD_CDN = {"cdn.discordapp.com", "media.discordapp.net"}


class ImageError(ValueError):
    pass


async def read_image(attachment) -> tuple[bytes, str]:
    image_type = (attachment.content_type or "").split(";", 1)[0].lower()
    if image_type not in IMAGE_TYPES:
        raise ImageError("Please attach a JPEG, PNG or WebP image.")
    if attachment.size <= 0 or attachment.size > MAX_IMAGE_BYTES:
        raise ImageError("Images must be smaller than 8 MiB.")
    parts = urlsplit(attachment.url)
    if parts.scheme != "https" or parts.hostname not in DISCORD_CDN or parts.username or parts.password or parts.port not in (None, 443):
        raise ImageError("The image must be a Discord attachment.")
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as session:
        async with session.get(attachment.url, allow_redirects=False) as response:
            response.raise_for_status()
            content = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                content.extend(chunk)
                if len(content) > MAX_IMAGE_BYTES:
                    raise ImageError("Images must be smaller than 8 MiB.")
    data = bytes(content)
    if image_type == "image/png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ImageError("The attached image is not a valid PNG.")
    if image_type == "image/jpeg" and not data.startswith(b"\xff\xd8\xff"):
        raise ImageError("The attached image is not a valid JPEG.")
    if image_type == "image/webp" and (len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"WEBP"):
        raise ImageError("The attached image is not a valid WebP.")
    return data, image_type


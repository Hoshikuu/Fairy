import asyncio
import unittest

from aiohttp.test_utils import TestClient, TestServer

from fairy.web.server import create_app
from fairy.web.screen import get_frame


class WebTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(TestServer(create_app()))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_information_page_and_assets_are_available(self):
        for path in ("/", "/assets/app.js", "/assets/style.css"):
            async with self.client.get(path) as response:
                self.assertEqual(response.status, 200, path)
                self.assertTrue(await response.read())

    async def test_removed_gateway_and_admin_routes_are_absent(self):
        for path in ("/api/admin", "/api/admin/history", "/api/health", "/v1/realtime"):
            async with self.client.get(path) as response:
                self.assertEqual(response.status, 404, path)
        async with self.client.post("/api/vision", json={}) as response:
            self.assertEqual(response.status, 404)

    async def test_foreign_origin_is_rejected(self):
        async with self.client.get("/", headers={"Origin": "https://unrelated.example"}) as response:
            self.assertEqual(response.status, 403)

    async def test_screen_rejects_invalid_discord_id(self):
        async with self.client.get("/api/screen?user_id=invalid") as response:
            self.assertEqual(response.status, 400)

    async def publish_frame(self, user_id):
        socket = await self.client.ws_connect(f"/api/screen?user_id={user_id}")
        await socket.send_bytes(b"\xff\xd8\xfftransport-test\xff\xd9")
        async with asyncio.timeout(2):
            while get_frame(user_id) is None:
                await asyncio.sleep(0.01)
        return socket

    async def test_closing_screen_socket_discards_frame(self):
        user_id = 123456789012345
        socket = await self.publish_frame(user_id)
        await socket.close()
        async with asyncio.timeout(2):
            while get_frame(user_id) is not None:
                await asyncio.sleep(0.01)

    async def test_web_shutdown_discards_active_screen(self):
        user_id = 123456789012346
        socket = await self.publish_frame(user_id)
        await self.client.close()
        self.assertTrue(socket.closed)
        self.assertIsNone(get_frame(user_id))

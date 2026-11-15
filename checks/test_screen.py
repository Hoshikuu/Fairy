import unittest
from unittest.mock import AsyncMock

from fairy.web import screen


class ScreenTests(unittest.IsolatedAsyncioTestCase):
    async def test_shutdown_closes_only_owned_shares_and_clears_frames(self):
        owned, other = AsyncMock(), AsyncMock()
        screen._frames[1] = screen.ScreenFrame(owned, "frame", 0)
        screen._frames[2] = screen.ScreenFrame(other, "other", 0)
        app = {screen.SCREEN_SHARES: {owned}}
        try:
            await screen.close_shares(app)
            self.assertNotIn(1, screen._frames)
            self.assertIn(2, screen._frames)
            self.assertEqual(app[screen.SCREEN_SHARES], set())
            owned.close.assert_awaited_once()
            other.close.assert_not_awaited()
        finally:
            screen._frames.clear()

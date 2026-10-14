import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import discord

import bot


def interaction(*, speak=True, muted=False):
    member = MagicMock(spec=discord.Member)
    channel = MagicMock(spec=discord.VoiceChannel)
    member.voice = SimpleNamespace(channel=channel)
    channel.permissions_for.return_value = SimpleNamespace(connect=True, speak=speak)
    text = MagicMock(spec=discord.TextChannel)
    text.permissions_for.return_value = SimpleNamespace(send_messages=True)
    guild = SimpleNamespace(id=1, me=SimpleNamespace(voice=SimpleNamespace(mute=muted)))
    return SimpleNamespace(user=member, guild=guild, channel=text,
                           response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
                           followup=SimpleNamespace(send=AsyncMock()))


class JoinTests(unittest.IsolatedAsyncioTestCase):
    async def test_requires_speak_permission(self):
        request = interaction(speak=False)
        await bot.join.callback(request)
        self.assertIn("Hablar", request.response.send_message.call_args.args[0])
        request.response.defer.assert_not_awaited()

    async def test_server_muted_bot_is_reported(self):
        request = interaction(muted=True)
        await bot.join.callback(request)
        self.assertIn("silenciado", request.response.send_message.call_args.args[0])
        request.response.defer.assert_not_awaited()

    async def test_offline_kokoro_is_reported_before_connecting(self):
        request = interaction()
        with patch("bot.check_kokoro", new=AsyncMock(side_effect=ValueError("voice mismatch"))):
            with self.assertLogs("bot", level="ERROR"):
                await bot.join.callback(request)
        request.response.defer.assert_awaited_once()
        self.assertIn("Kokoro", request.followup.send.call_args.args[0])
        request.user.voice.channel.connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()

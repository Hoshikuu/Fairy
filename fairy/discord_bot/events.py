"""Discord messages, voice-disconnect cleanup and readiness events."""

from __future__ import annotations

import discord
from fairy.clients.llama import ask_req


def register_events(bot):
    # @Fairy hello
    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot:
            return

        if bot.user in message.mentions:

            msg = message.content.replace(
                f"<@{bot.user.id}>",
                ""
            ).replace(
                f"<@!{bot.user.id}>",
                ""
            ).strip()

            if not msg:
                return

            print(f"User: {msg}")

            async with message.channel.typing():
                response = await ask_req(msg)

            await message.channel.send(response)
            return

        if "fairy" in message.content.lower():
            msg = message.content
            print(f"User: {msg}")

            async with message.channel.typing():
                response = await ask_req(msg)

            await message.channel.send(response)
            return

        await bot.process_commands(message)


    @bot.event
    async def on_voice_state_update(member, before, after):
        if member.id == bot.user.id and before.channel is not None and before.channel != after.channel:
            await bot.voice_manager.stop(member.guild.id)


    @bot.event
    async def on_ready():
        await bot.tree.sync()

        print(f"Bot ready as {bot.user}")

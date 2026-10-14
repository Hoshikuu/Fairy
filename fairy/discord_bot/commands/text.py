"""Text slash commands."""

from __future__ import annotations

import discord
from discord import app_commands
from fairy.clients.llama import ask_req


def register_commands(bot):
    # /ask hello
    @bot.tree.command(
        name="ask",
        description="Talk to Fairy"
    )
    @app_commands.allowed_installs(
        guilds=True,
        users=True
    )
    @app_commands.allowed_contexts(
        guilds=True,
        dms=True,
        private_channels=True
    )
    async def ask(
        interaction: discord.Interaction,
        message: str
    ):
        print(f"User: {message}")

        # Le dice a Discord que estamos procesando la respuesta
        await interaction.response.defer()

        response = await ask_req(message)

        await interaction.followup.send(response)

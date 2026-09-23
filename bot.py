import discord
from discord.ext import commands
from discord import app_commands

import os
from dotenv import load_dotenv

from cli import ask_req


load_dotenv()

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True


bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


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


@bot.event
async def on_ready():
    await bot.tree.sync()

    print(f"Bot ready as {bot.user}")


bot.run(TOKEN)
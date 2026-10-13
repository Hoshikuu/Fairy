import discord
from discord.ext import commands, voice_recv
from discord import app_commands

import os
import asyncio
import logging
from dotenv import load_dotenv

from cli import ask_req
from voice_transcription import VoiceTranscription


load_dotenv()

TOKEN = os.getenv("TOKEN")
WHISPER_URL = os.getenv("WHISPER_URL", "http://127.0.0.1:8081")
WHISPER_LANGUAGE = "en"
voice_sessions: dict[int, VoiceTranscription] = {}
voice_locks: dict[int, asyncio.Lock] = {}
whisper_lock = asyncio.Lock()
log = logging.getLogger(__name__)


async def stop_transcription(guild_id):
    session = voice_sessions.pop(guild_id, None)
    if session is not None:
        await session.stop()


class FairyBot(commands.Bot):
    async def close(self):
        await asyncio.gather(
            *(stop_transcription(guild_id) for guild_id in list(voice_sessions))
        )
        await super().close()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


bot = FairyBot(
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


@bot.tree.command(
    name="join",
    description="Join your voice channel and transcribe users with Whisper"
)
@app_commands.guild_only()
async def join(interaction: discord.Interaction):
    member = interaction.user
    if not isinstance(member, discord.Member) or member.voice is None or member.voice.channel is None:
        await interaction.response.send_message(
            "Entra primero en un canal de voz.", ephemeral=True
        )
        return

    channel = member.voice.channel
    guild = interaction.guild
    me = guild.me
    permissions = channel.permissions_for(me)
    if not permissions.connect:
        await interaction.response.send_message(
            "Necesito permiso para conectarme a ese canal.", ephemeral=True
        )
        return

    text_permissions = interaction.channel.permissions_for(me)
    can_send = (
        text_permissions.send_messages_in_threads
        if isinstance(interaction.channel, discord.Thread)
        else text_permissions.send_messages
    )
    if not can_send:
        await interaction.response.send_message(
            "Necesito permiso para enviar las transcripciones en este canal de texto.",
            ephemeral=True,
        )
        return

    await interaction.response.defer()
    async with voice_locks.setdefault(guild.id, asyncio.Lock()):
        voice_client = guild.voice_client
        session = voice_sessions.get(guild.id)
        if (
            isinstance(voice_client, voice_recv.VoiceRecvClient)
            and voice_client.is_connected()
            and voice_client.channel == channel
            and voice_client.is_listening()
            and session is not None
        ):
            session.text_channel = interaction.channel
            await interaction.followup.send(
                "Ya estoy escuchando tu canal de voz. Publicaré aquí las transcripciones."
            )
            return
        await stop_transcription(guild.id)
        try:
            if isinstance(voice_client, voice_recv.VoiceRecvClient) and voice_client.is_connected():
                if voice_client.channel != channel:
                    await voice_client.move_to(channel)
                await guild.change_voice_state(channel=channel, self_deaf=False)
            else:
                if voice_client is not None:
                    await voice_client.disconnect(force=True)
                voice_client = await channel.connect(
                    cls=voice_recv.VoiceRecvClient, self_deaf=False
                )
            session = VoiceTranscription(
                voice_client, interaction.channel, whisper_lock,
                server_url=WHISPER_URL, language=WHISPER_LANGUAGE,
            )
            session.start()
            voice_sessions[guild.id] = session
        except (discord.DiscordException, TimeoutError, OSError, RuntimeError):
            log.exception("Could not start voice transcription in guild %s", guild.id)
            if voice_client is not None:
                await voice_client.disconnect(force=True)
            await interaction.followup.send(
                "No he podido iniciar la recepción de voz. Revisa los permisos "
                "y las dependencias de voz del bot."
            )
            return

    await interaction.followup.send(
        f"Estoy escuchando {channel.mention}. Transcribiré con Whisper lo que "
        "hablen los usuarios y lo publicaré aquí. Usa /leave para detenerlo."
    )


@bot.tree.command(name="leave", description="Stop transcription and leave the voice channel")
@app_commands.guild_only()
async def leave(interaction: discord.Interaction):
    guild = interaction.guild
    voice_client = guild.voice_client
    if voice_client is None:
        await interaction.response.send_message("No estoy en un canal de voz.", ephemeral=True)
        return
    member = interaction.user
    if not isinstance(member, discord.Member) or member.voice is None or member.voice.channel != voice_client.channel:
        await interaction.response.send_message(
            "Entra en mi canal de voz para detener la transcripción.", ephemeral=True
        )
        return
    await interaction.response.defer()
    async with voice_locks.setdefault(guild.id, asyncio.Lock()):
        await stop_transcription(guild.id)
        voice_client = guild.voice_client
        if voice_client is not None:
            await voice_client.disconnect(force=True)
    await interaction.followup.send("He detenido la transcripción y salido del canal de voz.")


@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and before.channel is not None and before.channel != after.channel:
        await stop_transcription(member.guild.id)


@bot.event
async def on_ready():
    await bot.tree.sync()

    print(f"Bot ready as {bot.user}")


if __name__ == "__main__":
    bot.run(TOKEN)

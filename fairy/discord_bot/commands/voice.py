"""Voice join/leave commands and service availability checks."""

from __future__ import annotations

import logging
import discord
import httpx
from discord import app_commands
from discord.ext import voice_recv
from fairy.clients.kokoro import check_kokoro
from fairy.voice.session import VoiceTranscription
from ..permissions import join_error

log = logging.getLogger(__name__)


async def join(interaction: discord.Interaction, bot):
    error = join_error(interaction)
    if error:
        await interaction.response.send_message(error, ephemeral=True)
        return
    channel = interaction.user.voice.channel
    guild = interaction.guild
    settings = bot.settings
    manager = bot.voice_manager
    await interaction.response.defer()
    try:
        await check_kokoro(server_url=settings.kokoro_url, voice=settings.kokoro_voice)
    except (httpx.HTTPError, ValueError):
        log.exception("Kokoro is not ready for voice conversation")
        await interaction.followup.send(
            "Kokoro no está disponible o su voz no coincide con KOKORO_VOICE. "
            "Arranca main.py y revisa KOKORO_URL antes de usar /join."
        )
        return
    async with manager.lock_for(guild.id):
        voice_client = guild.voice_client
        session = manager.sessions.get(guild.id)
        if (
            isinstance(voice_client, voice_recv.VoiceRecvClient)
            and voice_client.is_connected()
            and voice_client.channel == channel
            and voice_client.is_listening()
            and session is not None
        ):
            session.text_channel = interaction.channel
            await interaction.followup.send(
                "Ya estoy escuchando tu canal de voz y responderé hablando."
            )
            return
        await manager.stop(guild.id)
        try:
            if isinstance(voice_client, voice_recv.VoiceRecvClient) and voice_client.is_connected():
                if voice_client.channel != channel:
                    await voice_client.move_to(channel)
                await guild.change_voice_state(channel=channel, self_deaf=False, self_mute=False)
            else:
                if voice_client is not None:
                    await voice_client.disconnect(force=True)
                voice_client = await channel.connect(
                    cls=voice_recv.VoiceRecvClient, self_deaf=False, self_mute=False
                )
            session = VoiceTranscription(
                voice_client, interaction.channel, manager.whisper_lock,
                server_url=settings.whisper_url, language=settings.whisper_language,
                kokoro_url=settings.kokoro_url, kokoro_voice=settings.kokoro_voice, kokoro_speed=settings.kokoro_speed,
            )
            session.start()
            manager.sessions[guild.id] = session
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
        "hablen los usuarios, publicaré la transcripción aquí y responderé "
        "hablando con Kokoro. Usa /leave para detenerlo."
    )


async def leave(interaction: discord.Interaction, bot):
    manager = bot.voice_manager
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
    async with manager.lock_for(guild.id):
        await manager.stop(guild.id)
        voice_client = guild.voice_client
        if voice_client is not None:
            await voice_client.disconnect(force=True)
    await interaction.followup.send("He detenido la transcripción y salido del canal de voz.")


def register_commands(bot):
    @bot.tree.command(name="join", description="Join your voice channel and answer with Kokoro")
    @app_commands.guild_only()
    async def join_command(interaction: discord.Interaction):
        await join(interaction, bot)

    @bot.tree.command(name="leave", description="Stop transcription and leave the voice channel")
    @app_commands.guild_only()
    async def leave_command(interaction: discord.Interaction):
        await leave(interaction, bot)

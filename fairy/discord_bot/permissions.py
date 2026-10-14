"""Voice and text permission checks for /join."""

from __future__ import annotations

import discord


def join_error(interaction):
    member = interaction.user
    if not isinstance(member, discord.Member) or member.voice is None or member.voice.channel is None:
        return "Entra primero en un canal de voz."

    channel = member.voice.channel
    if isinstance(channel, discord.StageChannel):
        return "Usa un canal de voz normal para conversar conmigo."
    guild = interaction.guild
    me = guild.me
    permissions = channel.permissions_for(me)
    if not permissions.connect:
        return "Necesito permiso para conectarme a ese canal."

    if not permissions.speak:
        return "Necesito el permiso Hablar en ese canal."
    if me.voice is not None and me.voice.mute:
        return "Estoy silenciado por el servidor. Quita el silencio antes de usar /join."

    text_permissions = interaction.channel.permissions_for(me)
    can_send = (
        text_permissions.send_messages_in_threads
        if isinstance(interaction.channel, discord.Thread)
        else text_permissions.send_messages
    )
    if not can_send:
        return "Necesito permiso para enviar las transcripciones en este canal de texto."

    return None

#                                                                    ---------------------------------
#
#                                                                       Script  creado por  Hoshiku
#                                                                       https://github.com/Hoshikuu
#
#                                                                    ---------------------------------

# event.py - V2.0

import discord
from discord.ext import commands

from time import time

from func.botconfig import configJson, GetPrefix
from func.database import select_db, update_db, insert_db
from models.views import VerificationView, VeriConfiView, ClosedTicketToolView
from models.embeds import SimpleEmbed
from func.logger import get_logger

logger = get_logger(__name__)

class Event(commands.Cog):
    """Contiene eventos de discord

    Args:
        commands (Cog): Cog
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_sessions = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        # Recargar las views de mensajes ya enviados
        try:
            self.bot.add_view(VerificationView())
            self.bot.add_view(VeriConfiView())
            self.bot.add_view(ClosedTicketToolView())
            logger.info("Views de event.py cargados correctamente")
        except Exception as e:
            logger.error(f"Error al cargar views antiguas de event.py: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.message.Message):
        """Se ejecuta cada vez que un usuario envía un mensaje

        Args:
            message (discord.message.Message): El mensaje enviado

        Raises:
            Exception: Cuando no se puede actualizar o insertar el contador de mensajes del usuario
        """

        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        
        # No hacer nada si el mensaje es de un bot
        if message.author.bot:
            return

        #! NO QUITAR ESTA LINEA YA QUE PREVIENE QUE EL BOT ENVÍE DOBLE MENSAJE
        if message.content[:len(GetPrefix(self.bot, message))] == GetPrefix(self.bot, message):
            return

        try:
            data = select_db(guild_id, "messages", "data", "id", user_id)
            
            if data:
                logger.debug(f"Aumentando el contador de mensajes del usuario {user_id}")
                if not update_db(guild_id, "data", "messages", data[0] + 1, "id", user_id):
                    raise Exception(f"No se ha podido actualizar el contador de mensajes del usuario {user_id}")
            else:
                logger.debug(f"Creando un nuevo registro para el usuario {user_id}")
                if not insert_db(guild_id, "data", "id, username, date, messages, voicechat", (user_id, message.author, message.author.joined_at.strftime("%d/%m/%Y"), 1, 0)):
                    raise Exception(f"No se ha podido insertar el contador de mensajes del usuario {user_id}")
        except Exception as e:
            logger.error(f"Error inesperado al manipular la base de datos: {e}")
        await self.bot.process_commands(message) #! NO SE QUE HACE PERO HAY QUE PONERLO

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.member.Member, before: discord.member.VoiceState, after: discord.member.VoiceState):
        """Se ejecuta cada vez que un usuario entra o sale de un canal de voz

        Args:
            member (discord.member.Member): Miembro que ha cambiado de estado
            before (discord.member.VoiceState): Canal de voz antes del cambio
            after (discord.member.VoiceState): Canal de voz después del cambio

        Raises:
            Exception: Cuando no se puede actualizar o insertar el tiempo de chat de voz del usuario
        """
        
        user_id = str(member.id)
        guild_id = str(member.guild.id)

        if before.channel is not None and after.channel is None:
            if user_id not in self.voice_sessions:
                print("Error: Usuario no registrado en voice_sessions") 
                return
            
            logger.debug(f"Usuario {user_id} salio del canal de voz {before.channel.id} del servidor {guild_id}")
            start_time = self.voice_sessions.pop(user_id)
            session_hours = float(time() - start_time) / 3600
            try:
                data = select_db(guild_id, "voicechat", "data", "id", user_id)
                
                if data:
                    logger.debug(f"Actualizando el tiempo de chat de voz del usuario {user_id} un total de {session_hours} horas")
                    if not update_db(guild_id, "data", "voicechat", data[0] + session_hours, "id", user_id):
                        raise Exception(f"No se ha podido actualizar el tiempo de chat de voz de usuario {user_id}")
                else:
                    logger.debug(f"Creando un nuevo registro para el usuario {user_id}")
                    if not insert_db(guild_id, "data", "id, username, date, messages, voicechat", (user_id, member.name, member.joined_at.strftime("%d/%m/%Y"), 0, session_hours)):
                        raise Exception(f"No se ha podido insertar el tiempo de chat de voz del usuario {user_id}")
            except Exception as e:
                logger.error(f"Error inesperado al manipular la base de datos: {e}")
        
        if before.channel is None and after.channel is not None:
            logger.debug(f"Usuario {user_id} entro al canal de voz {after.channel.id} del servidor {guild_id}")
            self.voice_sessions[user_id] = time()

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Se ejecuta cuando se crea un canal nuevo

        Args:
            channel (Channel): Canal nuevo que se crea
        """
        #TODO: Modificar esto cuando se actualize la configuración de tickets
        ticketConfigJson = configJson[str(channel.guild.id)]["ticket"]
        if channel.category_id == ticketConfigJson["category"]:
            if str(channel.name).split("-")[0] == ticketConfigJson["panels"]["verification"]["name"]:
                embed = SimpleEmbed("Verificación", "Inicia el proceso para obtener la información para poder completar la verificación.", discord.Color.blurple())
                await channel.send(f"<@{channel.topic}>", embed=embed, view=VerificationView())

async def setup(bot: commands.Bot):
    await bot.add_cog(Event(bot))
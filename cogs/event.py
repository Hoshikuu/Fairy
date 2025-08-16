from discord import Color
from discord.ext import commands

from time import time
from datetime import date

from func.botconfig import configJson, DefaultServerConfig, GetPrefix
from func.database import DatabaseConnect
from templates.views import VerificationView, VeriConfiView, ClosedTicketToolView
from templates.embeds import SimpleEmbed
from func.logger import get_logger

logger = get_logger(__name__)

# Comandos relacionados con eventos de discord
class Event(commands.Cog):
    """Contiene eventos de discord

    Args:
        commands (Cog): Cog
    """
    def __init__(self, bot):
        self.bot = bot
        self.voiceSessions = {}
    
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
    async def on_message(self, message):
        """Se ejecuta cada vez que recibe un mensaje

        Args:
            message (ctx): Mensaje
        """
        # Guarda los datos del mensaje en una variable
        userID = str(message.author.id)
        guildID = str(message.guild.id)
        username = str(message.author)

        # Crear la configuración del servidor si no tiene
        if guildID not in configJson:
            logger.warning(f"El servidor {message.guild.name} no tiene un json de configuración.")
            DefaultServerConfig(guildID)
        
        # Saltar si es un bot
        if message.author.bot: 
            return

        # Para evitar que doble ejecute el comando
        if message.content[:len(GetPrefix(self.bot, message))] == GetPrefix(self.bot, message):
            return

        conn = DatabaseConnect(guildID)
        cursor = conn.cursor()
        
        try:
            # Seleccionar los datos si no existe devuelve vacío
            cursor.execute("SELECT messages FROM data WHERE id = ?", (userID,))
            data = cursor.fetchone()
            logger.debug(f"Obteniendo los datos del usuario {userID}")
        except Exception as e:
            logger.error(f"Error al obtener los datos del usuario: {e}")
        
        try:
            if data: # Actualizar el contador de mensajes 
                newCount = data[0] + 1
                cursor.execute("UPDATE data SET messages = ? WHERE id = ?", (newCount, userID))
                logger.debug(f"Contador del usuario {userID} aumentado")
            else: # Añadir un nuevo registro si el usuario no existe
                cursor.execute("INSERT INTO data (id, username, date, messages, voicechat) VALUES (?, ?, ?, ?, ?)", (userID, username, message.author.joined_at.strftime("%d/%m/%Y"), 1, 0))
                cursor.execute("INSERT INTO economy (id, username, date, money) VALUES (?, ?, ?, ?)", (userID, username, date.today().strftime("%d/%m/%Y"), 100))
                logger.debug(f"Usuario {userID} añadido a la tabla")
        except Exception as e:
            logger.error(f"Error en aumentar el contador del usuario: {e}")

        conn.commit()
        
        await self.bot.process_commands(message) # Necesario en on_message para que se ejecute sin error

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Cuando un miembro cambia de chat de voz

        Args:
            member (Member): Miembro que hace el cambio de chat de voz
            before (Channel): Canal anterior
            after (Channel): Canal posterior
        """
        userID = str(member.id)
        guildID = str(member.guild.id)
        if before.channel is None and after.channel is not None:
            logger.debug(f"Usuario {userID} entro a un canal de voz")
            self.voiceSessions[userID] = time()
            
        elif before.channel is not None and after.channel is None:
            if userID in self.voiceSessions:
                logger.debug(f"Usuario {userID} salio de un chat de voz")
                startTime = self.voiceSessions.pop(userID)
                sessionHours = float(time() - startTime) / 3600

                conn = DatabaseConnect(guildID)
                cursor = conn.cursor()
                try:
                    # Seleccionar los datos si no existe devuelve vacío
                    cursor.execute(f"SELECT voicechat FROM data WHERE id = ?", (userID, ))
                    data = cursor.fetchone()
                except Exception as e:
                    logger.error(f"Error al obtener los datos: {e}")

                try:
                    if data: # Actualizar el contador de mensajes 
                        logger.debug(f"Actualizando el tiempo de chat de voz del usuario en {sessionHours}")
                        cursor.execute("UPDATE data SET voicechat = ? WHERE id = ?", (data[0] + sessionHours, userID))
                    else: # Añadir un nuevo registro si el usuario no existe
                        logger.debug(f"Creando un nuevo registro para el usuario {userID}")
                        cursor.execute("INSERT INTO data (id, username, date, messages, voicechat) VALUES (?, ?, ?, ?, ?)", (userID, member.name, member.joined_at.strftime("%d/%m/%Y"), 0, sessionHours))
                        cursor.execute("INSERT INTO economy (id, username, date, money) VALUES (?, ?, ?, ?)", (userID, member.name, date.today().strftime("%d/%m/%Y"), 100))

                except Exception as e:
                    logger.error(f"Error en añadir el tiempo de chat de voz al usuario {userID}: {e}")

                conn.commit()

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Se ejecuta cuando se crea un canal nuevo

        Args:
            channel (Channel): Canal nuevo que se crea
        """
        ticketConfigJson = configJson[str(channel.guild.id)]["ticket"]
        if channel.category_id == ticketConfigJson["category"]:
            if str(channel.name).split("-")[0] == ticketConfigJson["panels"]["verification"]["name"]:
                embed = SimpleEmbed("Verificación", "Inicia el proceso para obtener la información para poder completar la verificación.", Color.blurple())
                await channel.send(f"<@{channel.topic}>", embed=embed, view=VerificationView())

# Auto run
async def setup(bot):
    await bot.add_cog(Event(bot))
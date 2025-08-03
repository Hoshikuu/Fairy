# Modulo de discord
from discord import Color
from discord.ext import commands

# Modulo extra
from time import time

# Modulo de bot
from func.botconfig import configJson, DefaultServerConfig, GetPrefix
from func.database import DatabaseConnect
from templates.views import VerificationView, VeriConfiView, ClosedTicketToolView
from templates.embeds import SimpleEmbed
from func.logger import get_logger

logger = get_logger(__name__)

# Comandos relacionados con eventos de discord
class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voiceSessions = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        # Recargar las views de mensajes ya enviados
        self.bot.add_view(VerificationView())
        self.bot.add_view(VeriConfiView())
        self.bot.add_view(ClosedTicketToolView())
        logger.info("Views de event.py cargados correctamente")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        # Guarda los datos del mensaje en una variable
        userID = str(message.author.id)
        guildID = str(message.guild.id)
        username = str(message.author)

        # Crear la configuracion del servidor si no tiene
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
        
        # Seleccionar los datos si no existe devuelve vacio
        cursor.execute("SELECT messages FROM data WHERE id = ?", (userID,))
        data = cursor.fetchone()
        
        if data: # Actualizar el contador de mensajes 
            newCount = data[0] + 1
            cursor.execute("UPDATE data SET messages = ? WHERE id = ?", (newCount, userID))
        else: # Añadir un nuevo registro si el usuario no existe
            cursor.execute("INSERT INTO data (id, username, date, messages, voicechat) VALUES (?, ?, ?, ?, ?)", (userID, username, message.author.joined_at.strftime("%d/%m/%Y"), 1, 0))

        conn.commit()
        
        await self.bot.process_commands(message) # Necesario en on_message para que se ejecute sin error

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        userID = str(member.id)
        guildID = str(member.guild.id)
        if before.channel is None and after.channel is not None:
            logger.debug(f"Usuario {userID} entro a un canal de voz")
            self.voiceSessions[userID] = time()
            
        elif before.channel is not None and after.channel is None:
            try:
                if userID in self.voiceSessions:
                    logger.debug(f"Usuario {userID} salio de un chat de voz")
                    startTime = self.voiceSessions.pop(userID)
                    sessionHours = float(time() - startTime) / 3600

                    conn = DatabaseConnect(guildID)
                    cursor = conn.cursor()
                    try:
                        # Seleccionar los datos si no existe devuelve vacio
                        cursor.execute(f"SELECT voicechat FROM data WHERE id = ?", (userID, ))
                        data = cursor.fetchone()
                    except Exception as e:
                        logger.error(f"Error al obtener los datos: {e}")
                    
                    if data: # Actualizar el contador de mensajes 
                        logger.debug(f"Actualizando el tiempo de chat de voz del usuario en {sessionHours}")
                        cursor.execute("UPDATE data SET voicechat = ? WHERE id = ?", (data[0] + sessionHours, userID))
                    else: # Añadir un nuevo registro si el usuario no existe
                        logger.debug("Creando un nuevo registro para el usuario")
                        cursor.execute("INSERT INTO data (id, username, date, messages, voicechat) VALUES (?, ?, ?, ?, ?)", (userID, member.display_name, member.joined_at.strftime("%d/%m/%Y"), 0, sessionHours))

                    conn.commit()
            except Exception as e:
                logger.error(f"Error al añadir el tiempo de chat de voz al usuario {userID}: {e}")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        ticketConfigJson = configJson[str(channel.guild.id)]["ticket"]
        if channel.category_id == ticketConfigJson["category"]:
            if str(channel.name).split("-")[0] == ticketConfigJson["panels"]["verification"]["name"]:
                embed = SimpleEmbed("Verificación", "Inicia el proceso para obtener la información para poder completar la verificación.", Color.blurple())
                await channel.send(f"<@{channel.topic}>", embed=embed, view=VerificationView())

# Autorun
async def setup(bot):
    await bot.add_cog(Event(bot))
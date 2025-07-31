# Modulo de discord
from discord import Color
from discord.ext import commands

# Modulo extra
from time import time

# Modulo de bot
from func.terminal import printr
from func.botconfig import configJson, DefaultServerConfig, GetPrefix
from func.database import DatabaseConnect
from templates.views import VerificationView, VeriConfiView, ClosedTicketToolView
from templates.embeds import SimpleEmbed

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
        printr("Views de event.py cargados correctamente.", 1)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        # Guarda los datos del mensaje en una variable
        userID = str(message.author.id)
        guildID = str(message.guild.id)
        username = str(message.author)

        # Crear la configuracion del servidor si no tiene
        if guildID not in configJson:
            printr(f"El servidor {message.guild.name} no tiene un json de configuración.", 2)
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
        userID = member.id
        guildID = member.guild.id

        if before.channel is None and after.channel is not None:
            self.voiceSessions[userID] = time()
        elif before.channel is not None and after.channel is None:
            if userID in self.voiceSessions:
                startTime = self.voiceSessions.pop(userID)
                sessionHours = float(time() - startTime) / 360

                conn = DatabaseConnect(guildID)
                cursor = conn.cursor()

                # Seleccionar los datos si no existe devuelve vacio
                cursor.execute("SELECT voicechat FROM data WHERE id = ?", (userID))
                data = cursor.fetchone()
                
                if data: # Actualizar el contador de mensajes 
                    cursor.execute("UPDATE data SET voicechat = ? WHERE id = ?", (sessionHours, userID))
                else: # Añadir un nuevo registro si el usuario no existe
                    cursor.execute("INSERT INTO data (id, username, date, messages, voicechat) VALUES (?, ?, ?, ?, ?)", (userID, member.display_name, member.joined_at.strftime("%d/%m/%Y"), 0, sessionHours))

                conn.commit()

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
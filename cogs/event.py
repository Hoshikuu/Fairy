# Modulo de discord
import discord
from discord.ext import commands

from time import time

# Modulo de funciones
from func.terminal import printr
from func.botconfig import configJson, DefaultServerConfig, GetPrefix
from func.database import DatabaseConnect

from templates.views import VerificationView, VeriConfiView, ClosedTicketToolView

# Comandos relacionados con eventos de discord
class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voiceSessions = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view((VerificationView()))
        self.bot.add_view(VeriConfiView())
        self.bot.add_view(ClosedTicketToolView())
        printr("Views de event.py cargados correctamente.", 1)
    
    # Registrar cada mensaje de cada usuario exeptuando bots y comandos
    @commands.Cog.listener()
    async def on_message(self, message):
        # Se salta si es un BOT
        if message.author.bot: 
            printr(f"Mensaje es un BOT.", 2)
            return
        
        # Guarda los datos del mensaje en una variable
        userID = str(message.author.id)
        guildID = str(message.guild.id)
        username = str(message.author)

        # Comprobar que el servidor tenga una configuracion por defecto en el archivo de configuracion
        if guildID not in configJson:
            printr(f"El servidor {guildID} no tiene una configuración asignada.", 2)
            DefaultServerConfig(guildID)

        # Para evitar que doble ejecute el comando
        if message.content[:len(GetPrefix(self.bot, message))] == GetPrefix(self.bot, message):
            printr(f"Mensaje es un Comando.", 2)
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
        
        printr(f"Contado mensaje del usuario {userID} en el servidor {guildID}.", 1)
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
                cursor.execute("SELECT voicechat FROM data WHERE id = ?", (userID,))
                data = cursor.fetchone()
                
                if data: # Actualizar el contador de mensajes 
                    cursor.execute("UPDATE data SET voicechat = ? WHERE id = ?", (sessionHours, userID))
                else: # Añadir un nuevo registro si el usuario no existe
                    cursor.execute("INSERT INTO data (id, username, date, messages, voicechat) VALUES (?, ?, ?, ?, ?)", (userID, member.display_name, member.joined_at.strftime("%d/%m/%Y"), 1, 0))

                conn.commit()
                printr(f"Tiempo de chat de voz añadido al usuario {userID} en el servidor {guildID}.", 1)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        # Verificamos si el canal pertenece a la categoría de tickets
        if channel.category_id == configJson[str(channel.guild.id)]["ticket"]["category"]:
            if str(channel.name).split("-")[0] == "verificacion":
                embed = discord.Embed(
                    title="Verificación",
                    description="Para comenzar la verificación porfavor inicia el proceso.",
                    color=discord.Color.purple()
                )
                await channel.send(f"<@{channel.topic}>", embed=embed, view=VerificationView())

# Autorun
async def setup(bot):
    await bot.add_cog(Event(bot))
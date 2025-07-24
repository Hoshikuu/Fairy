import discord
from discord.ext import commands
from os.path import isfile

from func.terminal import now
from func.botconfig import configJson, DefaultServerConfig
from func.database import CreateDatabase, DatabaseConnect


class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
            
    # Registrar cada mensaje de cada usuario exeptuando bots
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: # Se salta si es un BOT
            print(f"{now()} WARN     Mensaje es un BOT.")
            return
        
        # Guarda los datos del mensaje en una variable
        userID = str(message.author.id)
        guildID = str(message.guild.id)
        username = str(message.author)
        
        if guildID not in configJson:
            print(f"{now()} WARN     El servidor {guildID} no tiene una configuración asignada.")
            DefaultServerConfig(guildID)
            print(f"{now()} INFO     Configuración por defecto creada para el servidor.")
        
        if not isfile(f"{guildID}.db"):
            print(f"{now()} WARN     Creando una nueva Base de Datos para {guildID}")
            CreateDatabase(guildID)
        
        conn = DatabaseConnect(guildID)
        cursor = conn.cursor()
        
        # Seleccionar los datos si no existe devuelve vacio
        cursor.execute("SELECT cantidad FROM mensajes WHERE user_id = ?", (userID,))
        data = cursor.fetchone()
        print(f"{now()} INFO     Datos de la base de datos obtenidos.")
        
        # PUTA MIERDA DE SQL
        if data: # Actualizar el contador de mensajes
            newCount = data[0] + 1
            cursor.execute("UPDATE mensajes SET cantidad = ? WHERE user_id = ?", (newCount, userID))
        else: # Añadir un nuevo registro
            cursor.execute("INSERT INTO mensajes (user_id, username, cantidad) VALUES (?, ?, ?)", (userID, username, 1))

        conn.commit()
        
        print(f"{now()} INFO     Contador del usuario {userID} del servidor {guildID} actualizado.")
        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(Event(bot))
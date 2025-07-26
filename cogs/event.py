# Modulo de discord
import discord
from discord.ext import commands

# Modulos extra
from os.path import isfile

# Modulo de funciones
from func.terminal import now
from func.botconfig import configJson, DefaultServerConfig
from func.database import CreateDatabase, DatabaseConnect

# Comandos relacionados con eventos de discord
class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    # Registrar cada mensaje de cada usuario exeptuando bots y comandos
    @commands.Cog.listener()
    async def on_message(self, message):
        # Se salta si es un BOT
        if message.author.bot: 
            print(f"{now()} WARN     Mensaje es un BOT.")
            return
        
        # Guarda los datos del mensaje en una variable
        userID = str(message.author.id)
        guildID = str(message.guild.id)
        username = str(message.author)

        if not isfile(f"database/{guildID}.db"):
            print(f"{now()} WARN     Creando una nueva Base de Datos para {guildID}")
            CreateDatabase(guildID)

        # Comprobar que el servidor tenga una configuracion por defecto en el archivo de configuracion
        if guildID not in configJson:
            print(f"{now()} WARN     El servidor {guildID} no tiene una configuración asignada.")
            DefaultServerConfig(guildID)

        # Para evitar que doble ejecute el comando
        if message.content.startswith(tuple(await self.bot.get_prefix(message))):
            print(f"{now()} WARN     Mensaje es un Comando.")
            return

        conn = DatabaseConnect(guildID)
        cursor = conn.cursor()
        
        # Seleccionar los datos si no existe devuelve vacio
        cursor.execute("SELECT cantidad FROM mensajes WHERE user_id = ?", (userID,))
        data = cursor.fetchone()
        print(f"{now()} INFO     Datos de la base de datos obtenidos.")
        
        if data: # Actualizar el contador de mensajes 
            newCount = data[0] + 1
            cursor.execute("UPDATE mensajes SET cantidad = ? WHERE user_id = ?", (newCount, userID))
        else: # Añadir un nuevo registro si el usuario no existe
            cursor.execute("INSERT INTO mensajes (user_id, username, cantidad) VALUES (?, ?, ?)", (userID, username, 1))

        conn.commit()
        
        print(f"{now()} INFO     Contador del usuario {userID} del servidor {guildID} actualizado.")
        await self.bot.process_commands(message) # Necesario en on_message para que se ejecute sin error

# Autorun
async def setup(bot):
    await bot.add_cog(Event(bot))
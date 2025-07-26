# Modulo de discord
import discord
from discord.ext import commands

# Modulo de funciones
from func.terminal import printr
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
        if message.content.startswith(tuple(await self.bot.get_prefix(message))):
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

# Autorun
async def setup(bot):
    await bot.add_cog(Event(bot))
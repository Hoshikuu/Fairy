# Modulo de discord
import discord
from discord.ext import commands

from time import time

from func.database import DatabaseConnect
from func.terminal import printr

# Template for cog
class Voicechat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voiceSessions = {}

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

# Autorun
async def setup(bot):
    await bot.add_cog(Voicechat(bot))
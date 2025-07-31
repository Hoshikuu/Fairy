# Modulo de discord
import discord
from discord.ext import commands

# Modulo de funciones
from func.botconfig import CheckSetUp, IsSU
from func.terminal import printr
from func.database import DatabaseConnect

# Comandos relacionados a mensajes de texto
class Textchat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # TODO: Deberia pensar en un nombre mejor para este comando no me gusta esto
    # Comando para mostrar el contador de mensajes de cada usuario
    @commands.hybrid_command(name="count", description="Muestra el contador de mensajes.")
    @IsSU() # Funcion para comprobar si el usuario tiene el de super usuario
    async def count(self, ctx):
        # Prevenir la ejecucion de comandos si no esta configurado el bot.
        if CheckSetUp(ctx):
            await ctx.send("Porfavor use el comando /setup o hs$setup, antes de ejecutar ningun comando.", reference=ctx.message)
            return
        
        conn = DatabaseConnect(ctx.guild.id)
        cursor = conn.cursor()

        cursor.execute("SELECT username, messages, voicechat FROM data ORDER BY messages DESC")
        datos = cursor.fetchall() # Obtiene los datos de cantidad de mensajes de todos los usuarios
        
        # UFFFF EMBEDS QUE BONITOS POR DIOS
        embed = discord.Embed(
            title="Contador Mensajes",
            description="",
            color=discord.Color.blue()  # HEX: discord.Color.from_rgb(0,0,0)
        )

        # Muestra el usuario y la cantidad de mensajes enviado en una pantalla de descripcion
        # TODO: Pa futuro separarlos en varias paginas para mejor legibilidad
        text = ""
        for i, (username, cantidad, voicechat) in enumerate(datos, start=1):
            text += f"**{i}** {username} — **{cantidad} mensajes** — **{voicechat}** horas\n"
        embed.description = text
        printr(f"Mostrando datos del contador en el Discord.", 1)
        await ctx.send(embed=embed, reference=ctx.message)

    # Esto indica si la funcion da error ejecutar esto
    @count.error
    # Error de permisos, Falta de permisos
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
            embed = discord.Embed(
                title="Permiso Denegado",
                description="No tienes permisos para ejecutar este comando.",
                color=discord.Color.red()  # HEX: discord.Color.from_rgb(0,0,0)
            )
            printr(f"Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando.", 4)
            await ctx.send(embed=embed, reference=ctx.message)

# Autorun
async def setup(bot):
    await bot.add_cog(Textchat(bot))
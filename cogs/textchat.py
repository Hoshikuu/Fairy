# Modulo de discord
from discord import Color
from discord.ext import commands

# Modulo de funciones
from func.botconfig import CheckSetUp, IsSU
from func.database import DatabaseConnect
from func.logger import get_logger
from templates.embeds import SimpleEmbed

logger = get_logger(__name__)

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
        
        try:
            conn = DatabaseConnect(ctx.guild.id)
            cursor = conn.cursor()

            cursor.execute("SELECT username, messages, voicechat FROM data ORDER BY messages DESC")
            datos = cursor.fetchall() # Obtiene los datos de cantidad de mensajes de todos los usuarios
        except Exception as e:
            logger.error(f"Error con la base de datos: {e}")
        
        # UFFFF EMBEDS QUE BONITOS POR DIOS
        embed = SimpleEmbed("Contador Mensajes", "", Color.blue())

        try:
            # Muestra el usuario y la cantidad de mensajes enviado en una pantalla de descripcion
            # TODO: Pa futuro separarlos en varias paginas para mejor legibilidad
            text = ""
            logger.debug("Concatenando el mensaje de contador")
            for i, (username, cantidad, voicechat) in enumerate(datos, start=1):
                text += f"**{i}** {username} — **{cantidad} mensajes** — **{voicechat}** horas\n"
            embed.description = text
            logger.info("Mostrando informacion del contador")
            await ctx.send(embed=embed, reference=ctx.message)
        except Exception as e:
            logger.error(f"Error inesperado en enviar el mensaje resultado: {e}")

    # Esto indica si la funcion da error ejecutar esto
    @count.error
    # Error de permisos, Falta de permisos
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
            embed = SimpleEmbed("Permiso Denegado", "No tienes permisos para ejecutar este comando", Color.red())
            logger.error(f"Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando.")
            await ctx.send(embed=embed, reference=ctx.message)

# Autorun
async def setup(bot):
    await bot.add_cog(Textchat(bot))
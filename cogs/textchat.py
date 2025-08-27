from discord import Color
from discord.ext import commands
from discord.utils import escape_markdown

from func.botconfig import CheckSetUp
from func.database import DatabaseConnect
from func.logger import get_logger
from templates.embeds import SimpleEmbed

logger = get_logger(__name__)

class Textchat(commands.Cog):
    """Comandos relacionado a los mensajes de texto

    Args:
        commands (Cog): Cog
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="top", description="Muestra el contador de mensajes y chat de voz.")
    async def top(self, ctx):
        """Muestra la cantidad de mensajes escritos por cada usuario

        Args:
            ctx (ctx): Mensaje
        """
        # Prevenir la ejecución de comandos si no esta configurado el bot.
        if CheckSetUp(ctx):
            await ctx.send("Por favor use el comando /setup o hs$setup, antes de ejecutar ningún comando.", reference=ctx.message)
            return
        
        try:
            conn = DatabaseConnect(ctx.guild.id)
            cursor = conn.cursor()

            cursor.execute("SELECT username, messages, voicechat FROM data ORDER BY messages DESC")
            datos = cursor.fetchall() # Obtiene los datos de cantidad de mensajes de todos los usuarios
        except Exception as e:
            logger.error(f"Error con la base de datos: {e}")
        
        embed = SimpleEmbed("Contador Mensajes", "", Color.blue())

        try:
            # Muestra el usuario y la cantidad de mensajes enviado en una pantalla de descripción
            # TODO: Pa futuro separarlos en varias paginas para mejor legibilidad
            # TODO: Añadir un registro de cuando se comienza a registrar los mensajes, actualizar el registro después de hacer export
            text = ""
            logger.debug("Concatenando el mensaje de contador")
            for i, (username, cantidad, voicechat) in enumerate(datos, start=1):
                text += f"**{i}** {escape_markdown(username)} — **{cantidad} mensajes** — **{int(voicechat * 100) / 100}** horas\n"
            embed.description = text
            logger.info("Mostrando información del contador")
            await ctx.send(embed=embed, reference=ctx.message)
        except Exception as e:
            logger.error(f"Error inesperado en enviar el mensaje resultado: {e}")

    # Esto indica si la función da error ejecutar esto
    @top.error
    # Error de permisos, Falta de permisos
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
            embed = SimpleEmbed("Permiso Denegado", "No tienes permisos para ejecutar este comando", Color.red())
            logger.error(f"Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando.")
            await ctx.send(embed=embed, reference=ctx.message)

# Auto run
async def setup(bot):
    await bot.add_cog(Textchat(bot))
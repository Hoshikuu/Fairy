# Modulos de discord
from discord import Color
from discord.ext import commands

# Modulo de funciones
from func.botconfig import configJson, IsSU, DefaultServerConfig
from func.logger import get_logger
from templates.views import SetupView
from templates.embeds import SimpleEmbed

logger = get_logger(__name__)

class Settings(commands.Cog):
    """Comandos relacionados con la configuración del bot

    Args:
        commands (Cog): Cog
    """
    def __init__(self, bot):
        self.bot = bot
        
    @commands.hybrid_command(name="setup", description="Inicia la configuración interactiva del bot.")
    @IsSU()
    async def setup(self, ctx):
        """Comando para configurar el bot en el servidor

        Args:
            ctx (ctx): Mensaje
        """
        try:
            if str(ctx.guild.id) not in configJson:
                logger.warning(f"El servidor {ctx.guild.id} no tiene un json de configuración")
                DefaultServerConfig(ctx.guild.id)

            view = SetupView(authorID=ctx.author.id, guildID=ctx.guild.id)
            msg = await ctx.send(embed=view.embed, view=view, ephemeral=False)
            view.message = msg
        except Exception as e:
            logger.critical(f"Si solo ves este mensaje de error, este error es muy inesperado en el script: {e}")
            return
        
    # Esto indica si la función da error ejecutar esto
    @setup.error
    # Error de permisos, Falta de permisos
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
            logger.error(f"Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando")
            embed = SimpleEmbed("Permiso Denegado", "No tienes permisos para ejecutar este comando.", Color.red())
            await ctx.send(embed=embed, reference=ctx.message)

# Auto run
async def setup(bot):
    await bot.add_cog(Settings(bot))
from discord import Color
from discord.ext import commands

from func.version import __tag__, __commit__, __branch__
from func.logger import get_logger
from models.embeds import SimpleEmbed

logger = get_logger(__name__)


class About(commands.Cog):
    """Comandos de información del bot

    Args:
        commands (Cog): Cog
    """
    def __init__(self, bot):
        self.bot = bot

    # Información básica del bot
    @commands.hybrid_command(name="info", description="Muestra la información básica del bot")
    async def info(self, ctx):
        """Muestra información del bot

        Args:
            ctx (ctx): Mensaje
        """
        logger.debug("Ejecutando comando info")
        embed = SimpleEmbed("Fairy", "Un bot privado para el servidor Fairy.", Color.dark_blue())
        embed.add_field(name="Ping", value=f"{round(ctx.bot.latency * 1000)}ms", inline=False)
        embed.add_field(name="Creador", value="<@853193606529024041>", inline=True)
        embed.set_footer(text="Suban me el sueldo.")
        await ctx.send(embed=embed)

    # Muestra la versión actual del bot
    @commands.hybrid_command(name="version", description="Muestra la versión actual del bot")
    async def version(self, ctx):
        """Muestra la versión del bot

        Args:
            ctx (ctx): Mensaje
        """
        logger.debug("Ejecutando comando version")
        embed = SimpleEmbed("Fairy", f"Actualmente estoy en la versión {__tag__} !", Color.magenta())
        embed.add_field(name="GitHub", value="https://github.com/Hoshikuu/Fairy", inline=True)
        embed.set_footer(text="A futuro más y mejor.")
        await ctx.send(embed=embed)  

# Auto run
async def setup(bot):
    await bot.add_cog(About(bot))
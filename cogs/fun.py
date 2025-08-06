# Modulos de discord
from discord import Color
from discord.ext import commands

from datetime import timedelta, datetime

# Modulos del bot
from func.logger import get_logger
from templates.embeds import SimpleEmbed

logger = get_logger(__name__)

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="suicide", description="Aislarse 1 minuto al ejecutar.")
    async def suicide(self, ctx):
        try:
            # await ctx.author.timeout(timedelta(minutes=1))
            logger.info(f"{ctx.author.id} se ha suicidado")
            embed = SimpleEmbed(f"{ctx.author} se ha suicidado.", "", Color.blue())
            embed.set_image(url="https://media.tenor.com/EjFzN8O9tjgAAAAC/persona-3-im-gonna-persona-3-myself.gif")
            embed.timestamp = datetime.now()
            await ctx.send(embed=embed, reference=ctx.message)
        except Exception as e:
            logger.error(f"Ha ocurrido un error inesperado: {e}")

# Autorun
async def setup(bot):
    await bot.add_cog(Fun(bot))
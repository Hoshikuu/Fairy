# Modulos de discord
from discord import Color
from discord.ext import commands

from datetime import timedelta, datetime
from random import choice

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
            gifs = ["https://media.tenor.com/YTWHmcGTfu8AAAAd/persona-persona3.gif", "https://media.tenor.com/EjFzN8O9tjgAAAAC/persona-3-im-gonna-persona-3-myself.gif", "https://media.tenor.com/Bsb9Z2NL0mUAAAAd/suicide-family-guy.gif", "https://media.tenor.com/s2R8VviOrwEAAAAd/fml-buenos.gif", "https://media.tenor.com/upyhim0-CUAAAAAd/spamton-deltarune.gif", "https://media.tenor.com/UlIwB2YVcGwAAAAd/waah-waa.gif"]
            logger.info(f"{ctx.author.id} se ha suicidado")
            embed = SimpleEmbed(f"{ctx.author.display_name} se ha suicidado.", "", Color.blue())
            embed.set_image(url=choice(gifs))
            embed.timestamp = datetime.now()
            await ctx.send(embed=embed, reference=ctx.message)
        except Exception as e:
            logger.error(f"Ha ocurrido un error inesperado: {e}")

# Autorun
async def setup(bot):
    await bot.add_cog(Fun(bot))
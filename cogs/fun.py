# Modulos de discord
from discord import Color
from discord.ext import commands, tasks

from datetime import timedelta, datetime
from random import choice, randint
from numpy import arange
from asyncio import sleep

# Modulos del bot
from func.logger import get_logger
from func.database import CreateRouletteDatabase
from templates.embeds import SimpleEmbed

logger = get_logger(__name__)

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.rouletteNumber.start()
    
    @commands.hybrid_command(name="suicide", description="Aislarse 1 minuto al ejecutar.")
    async def suicide(self, ctx):
        try:
            await ctx.author.timeout(timedelta(minutes=1))
            gifs = ["https://media.tenor.com/YTWHmcGTfu8AAAAd/persona-persona3.gif", "https://media.tenor.com/EjFzN8O9tjgAAAAC/persona-3-im-gonna-persona-3-myself.gif", "https://media.tenor.com/Bsb9Z2NL0mUAAAAd/suicide-family-guy.gif", "https://media.tenor.com/s2R8VviOrwEAAAAd/fml-buenos.gif", "https://media.tenor.com/upyhim0-CUAAAAAd/spamton-deltarune.gif", "https://media.tenor.com/UlIwB2YVcGwAAAAd/waah-waa.gif"]
            logger.info(f"{ctx.author.id} se ha suicidado")
            embed = SimpleEmbed(f"{ctx.author.display_name} se ha suicidado.", "", Color.blue())
            embed.set_image(url=choice(gifs))
            embed.timestamp = datetime.now()
            await ctx.send(embed=embed, reference=ctx.message)
        except Exception as e:
            logger.error(f"Ha ocurrido un error inesperado: {e}")
            
    @commands.hybrid_command(name="random", description="Te da un numero aleatorio entre un rango designada.")
    async def random(self, ctx, min = 1, max = 10):
        try:
            number = randint(min, max)
            logger.debug(f"Numero aleatorio es {number}")
            await ctx.send(f"Tu numero es: {number}", reference=ctx.message)
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            
    # Daily Roulete
    @commands.hybrid_command(name="roulette", description="Ruleta diaria")
    async def roulette(self, ctx, number):
        try:
            CreateRouletteDatabase(ctx.guild.id)
            
            
            await ctx.send(f"{number}", reference=ctx.message)
        except Exception as e:
            logger.error(f"Ha ocurrido un error inesperado: {e}")
    
    @tasks.loop(hours=24)
    async def rouletteNumber(self):
        try:
            ahora = datetime.now()
            proxima_medianoche = (ahora + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            espera = (proxima_medianoche - ahora).total_seconds()
            await sleep(espera)
            roulette = arange(0, 37).tolist()
                
            number = choice(roulette)
            canal = self.bot.get_channel(1013956260070174742)
            if canal:
                await canal.send(f"El numero de la ruleta es {number}")
        except Exception as e:
            logger.error(f"Ha ocurrido un error inesperado: {e}")
            
    @rouletteNumber.before_loop
    async def beforeRouletteNumber(self):
        await self.bot.wait_until_ready()

# Autorun
async def setup(bot):
    await bot.add_cog(Fun(bot))
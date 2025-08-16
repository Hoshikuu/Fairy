from discord import Color
from discord.ext import commands

from datetime import timedelta, datetime
from random import choice, randint

from func.logger import get_logger
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
        """Comando para suicidarte te aísla por un minuto

        Args:
            ctx (ctx): Mensaje
        """
        try:
            await ctx.author.timeout(timedelta(minutes=1))
            # Gifs de rotación para el comando
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
        """Decide un numero aleatorio entre los limites establecidos

        Args:
            ctx (ctx): Mensaje
            min (int, optional): Limite mínimo. Defaults to 1.
            max (int, optional): Limite Máximo. Defaults to 10.
        """
        try:
            # Decide un numero aleatorio entre el limite
            number = randint(min, max)
            logger.debug(f"Numero aleatorio es {number}")
            await ctx.send(f"Tu numero es: {number}", reference=ctx.message)
        except Exception as e:
            logger.error(f"Error inesperado: {e}")
            
    # Daily Roulette
    @commands.hybrid_command(name="roulette", description="Ruleta diaria")
    async def roulette(self, ctx, number):
        # TODO: Guardar el numero que se introduce a la ruleta
        
        try:
            await ctx.send(f"{number}", reference=ctx.message)
        except Exception as e:
            logger.error(f"Ha ocurrido un error inesperado: {e}")
    
    

# Auto run
async def setup(bot):
    await bot.add_cog(Fun(bot))
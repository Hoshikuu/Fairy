from discord.ext import commands, tasks

from datetime import timedelta, datetime
from random import choice
from numpy import arange
from asyncio import sleep

from func.logger import get_logger

logger = get_logger(__name__)

class Gambling(commands.Cog):
    """Comandos relacionados a las apuestas

    Args:
        commands (Cog): Cog
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.rouletteNumber.start()
        
    @tasks.loop(hours=24)
    async def rouletteNumber(self):
        """Se ejecuta cada 24horas para dar los resultados de la ruleta
        """
        # HACK: Comprobar que esto funcione cada 24 horas
        try:
            ahora = datetime.now()
            proxima_medianoche = (ahora + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0) # Sincroniza el tiempo para que sea 0:00
            espera = (proxima_medianoche - ahora).total_seconds()
            await sleep(espera)
            # FIXME: Arreglar ruleta
            roulette = arange(0, 37).tolist()
                
            number = choice(roulette)
            canal = self.bot.get_channel(1013956260070174742) # TODO: Añadir esto a botconfig
            if canal:
                await canal.send(f"El numero de la ruleta es {number}")
        except Exception as e:
            logger.error(f"Ha ocurrido un error inesperado: {e}")
            
    @rouletteNumber.before_loop
    async def beforeRouletteNumber(self):
        # Ejecuta el loop de 24 horas
        await self.bot.wait_until_ready()
        
# Auto run
async def setup(bot):
    await bot.add_cog(Gambling(bot))
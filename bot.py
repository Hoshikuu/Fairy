#                                                                    ---------------------------------
#
#                                                                       Script  creado por  Hoshiku
#                                                                       https://github.com/Hoshikuu
#
#                                                                    ---------------------------------

# bot.py - V2.0

from discord import Intents
from discord.ext import commands

from os import listdir, getenv
from asyncio import run
from dotenv import load_dotenv

from func.botconfig import GetPrefix
from func.logger import get_logger

logger = get_logger(__name__)
bot = commands.Bot(command_prefix=GetPrefix, intents=Intents.all())

@bot.event
async def on_ready():
    """Evento que se ejecuta cuando el bot se conecta a Discord
    """
    try:
        synced = await bot.tree.sync()
        logger.info(f"Sincronizados {len(synced)} comandos")
    except Exception as e:
        logger.error(f"Error al sincronizar comandos: {e}")

    logger.info(" === FAIRY CONECTADO ===")

async def main():
    """Función principal para iniciar el bot de Discord
    """
    async with bot:
        for cog in listdir("./cogs"):
            if cog.endswith(".py"):
                try:
                    await bot.load_extension(f"cogs.{cog[:-3]}")
                    logger.info(f"{cog} cargado a los cogs")
                except Exception as e:
                    logger.critical(f"{cog} cog no se pudo cargar, es posible que algunos comandos y funcionalidades dejen de funcionar: {e}")
                
        logger.info("Todos los cogs posibles han sido cargados")
        
        try:
            load_dotenv()
            await bot.start(getenv("DISCORD_TOKEN"))
            logger.info("Recuperando token de entorno y arrancando el bot")
        except Exception as e:
            logger.critical(f"El bot no se ha podido iniciar, revise el token y vuelva a intentarlo: {e}")
            exit(1)

if __name__ == "__main__":
    logger.info("Iniciando Fairy ...")
    run(main())
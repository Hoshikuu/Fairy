# Modulos de discord para manejar el Bot
from discord import Intents
from discord.ext import commands

# Modulos Extras
from os import listdir, getenv
from asyncio import run
from dotenv import load_dotenv

# Modulo de funciones
from func.botconfig import GetPrefix, ChargeConfig, configJson
from func.logger import get_logger

# TODO: Añadir embeds a los mensajes enviados de vuelta

# Logger centralizado
logger = get_logger(__name__)

# Carga la configuracion inicial
ChargeConfig()
logger.info("Configuración inical cargada")

# El bot obtiene todos los permisos disponibles
bot = commands.Bot(command_prefix=GetPrefix, intents=Intents.all())
logger.debug("Permisos del bot establecidos.")

# Obtener el token del bot
def GetToken():
    load_dotenv()
    token = getenv("DISCORD_TOKEN")
    logger.info("Token del bot obtenido")
    return token

# Carga los cogs del bot automaticamente
async def ChargeCogs():
    for cog in listdir("./cogs"):
        if not cog.endswith(".py"): # Busca los archivos de python y los carga al bot
            continue
        try:
            await bot.load_extension(f"cogs.{cog[:-3]}")
            logger.info(f"{cog} cargado a los cogs")
        except Exception as e:
            logger.critical(f"{cog} cog no se pudo cargar, es posible que algunos comandos y funcionalidades dejen de funcionar: {e}")

# Funcion principal para ejecutar el bot
async def main():
    async with bot:
        await ChargeCogs()
        logger.info("Todos los cogs cargados correctamente")
        await bot.start(GetToken())

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        logger.info(f"Sincronizados {len(synced)} comandos")
    except Exception as e:
        logger.error(f"Error al sincronizar comandos: {e}")
    
    for guild in bot.guilds:
        logger.debug(f"Conectado al servidor: {guild.name} con id: {guild.id}")

    logger.info(" === BOT CONECTADO ===")

# Inicia el bot
if __name__ == "__main__":
    logger.info("Iniciando Bot HoyoStars")
    run(main())
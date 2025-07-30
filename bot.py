# Modulos de discord para manejar el Bot
import discord
from discord.ext import commands

# Modulos Extras
from os import listdir
from asyncio import run

# Modulo de funciones
from config import GetToken
from func.terminal import printr
from func.botconfig import GetPrefix, ChargeConfig, configJson

# TODO: Añadir embeds a los mensajes enviados de vuelta

# TODO: Añadir el Rich a la terminal para un mejor output
# --------------------
# 1 -> INFO -> Information
# 2 -> WARN -> Warning
# 3 -> ERRO -> Error
# 4 -> EXEP -> Exeption
# --------------------

#* Se carga antes de inicializar el bot, para evitar problemas con la variable de configuracion en otro script
ChargeConfig()
printr(f"Fichero de configuración cargado.", 1)

# El bot obtiene todos los permisos disponibles
# TODO: Investigar para asignar solo los permisos necesarios
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=GetPrefix, intents=intents)
printr(f"Permisos del Bot establecidos.", 1)

# Mensaje que se muestra cuando el bot esta iniciado
# Muestra los comandos sincronizados en el command tree del discord
# Muestra en los servidores que esta sirviendo el bot
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        printr(f"Sincronizados {len(synced)} comandos.", 1)
    except Exception as e:
        printr(f"Error al sincronizar comandos: {e}.", 3)
        
    printr(f"Bot conectado como {bot.user}.", 1)
    
    for guild in bot.guilds:
        printr(f"Conectado al servidor: {guild.name} con id: {guild.id}.", 1)

    printr(f"BOT listo para usarse.", 1)

# Carga los cogs del bot automaticamente
async def ChargeCogs():
    for cog in listdir("./cogs"):
        if cog.endswith(".py"): # Busca los archivos de python y los carga al bot
            printr(f"Cargando el archivo {cog} al bot.", 1)
            await bot.load_extension(f"cogs.{cog[:-3]}")

# Funcion principal para ejecutar el bot
async def main():
    async with bot:
        await ChargeCogs()
        printr(f"Cogs cargados correctamente al bot.", 1)
        await bot.start(GetToken())

# Inicia el bot
if __name__ == "__main__":
    printr(f"Iniciando Bot HoyoStars.", 1)
    run(main())
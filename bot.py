# Modulos de discord para manejar el Bot
import discord
from discord.ext import commands

# Modulos Extras
from os import listdir
from asyncio import run

# Modulo de funciones
from config import GetToken
from func.terminal import now
from func.botconfig import GetPrefix, ChargeConfig

# TODO: Añadir el Rich a la terminal para un mejor output
# --------------------
# INFO-> Information
# WARN-> Warning
# ERRO-> Error
# EXEP-> Exeption
# --------------------

#* Se carga antes de inicializar el bot, para evitar problemas con la variable de configuracion en otro script
ChargeConfig()
print(f"{now()} INFO     Fichero de configuración cargado.")

# El bot obtiene todos los permisos disponibles
# TODO: Investigar para asignar solo los permisos necesarios
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=GetPrefix, intents=intents)
print(f"{now()} INFO     Permisos del Bot establecidos.")

# Mensaje que se muestra cuando el bot esta iniciado
# Muestra los comandos sincronizados en el command tree del discord
# Muestra en los servidores que esta sirviendo el bot
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"{now()} INFO     Sincronizados {len(synced)} comandos.")
    except Exception as e:
        print(f"{now()} ERRO     Error al sincronizar comandos: {e}.")
        
    print(f"{now()} INFO     Bot conectado como {bot.user}.")
    
    for guild in bot.guilds:
        print(f"{now()} INFO     Conectado al servidor: {guild.name} con id: {guild.id}.")
        
    print(f"{now()} INFO     BOT listo para usarse.")

# Carga los cogs del bot automaticamente
async def ChargeCogs():
    for cog in listdir("./cogs"):
        if cog.endswith(".py"): # Busca los archivos de python y los carga al bot
            print(f"{now()} INFO     Cargando el archivo {cog} al bot.")
            await bot.load_extension(f"cogs.{cog[:-3]}")

# Funcion principal para ejecutar el bot
async def main():
    async with bot:
        await ChargeCogs()
        print(f"{now()} INFO     Cogs cargados correctamente al bot.")
        await bot.start(GetToken())

# Inicia el bot
if __name__ == "__main__":
    print(f"{now()} INFO     Iniciando Bot HoyoStars.")
    run(main())
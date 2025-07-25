import discord
from discord.ext import commands
from func.terminal import now
from func.botconfig import GetPrefix
from config import GetToken
from os import listdir

from func.botconfig import ChargeConfig

# TODO: Algo de rich print para que haga prints en colores en la terminal en teoria es un momento el modulo solo habra que cambiar todo y es una pereza
# ---------------------------------------------------------------------------------------
# 
# INFO-> Information
# WARN-> Warning
# ERRO-> Error
# EXEP-> Exeption
# 
# ---------------------------------------------------------------------------------------

# ME DA PALO HACER QUE USE LOS PERMISOS ESPECIFICOS ASI QUE LE DOY TODOS LOS PERMISOS
# Permisos del bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=GetPrefix, intents=intents) # TODO: Cambia el sufijo porfavor que me cuesta escribirlo
print(f"{now()} INFO     Permisos del Bot establecidos.")

# Cargo la informacion ya que de antes no la pude cargar porque la funcion aun no estaba definida
ChargeConfig()
print(f"{now()} INFO     Fichero de configuración cargado.")

# Para mostrar en que servidores esta sirviendo el bot
# NO LO VA A USAR NADIE PORQUE HAGO ESTO
# Mensaje de inicio
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

# Cargar automáticamente todos los cogs de la carpeta "cogs"
async def cargar_cogs():
    for archivo in listdir("./cogs"):
        if archivo.endswith(".py"):
            print(archivo)
            await bot.load_extension(f"cogs.{archivo[:-3]}")
    
async def main():
    async with bot:
        await cargar_cogs()
        print(f"{now()} INFO     Iniciando Bot HoyoStars.")
        await bot.start(GetToken())

import asyncio
asyncio.run(main())
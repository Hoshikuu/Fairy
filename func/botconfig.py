from discord.ext import commands

# Modulos para gestionar JSON
from json import load, dump
from os.path import isfile

# Modulo de funciones
from func.logger import get_logger

# Variable que se usa globalmente para poder acceder al contenido del archivo de configuracion del bot
configJson = None
logger = get_logger(__name__)

# Crea el fichero si no existe
def CheckFile():
    if isfile("botconfig.json"):
        return
    
    logger.warning("Fichero de configuración no esta creado")
    with open("botconfig.json", "w", encoding="utf-8") as file:
        logger.debug("Creando fichero de configuracion")
        file.write("{}")
        logger.info("Fichero de configuración creado")

# TODO: Que se pueda cambiar dinamicamente el nombre del archivo de configuracion
# Carga el archivo de configuracion en la variable global, Se puede llamar en ejecucion para recargar el archivo de configuracion
def ChargeConfig():
    try:
        CheckFile()
        global configJson # Para poder modificar la variable

        # Lee el contenido del json y lo carga a la variable
        with open("botconfig.json", "r", encoding="utf-8") as file:
            configJson = load(file)
            logger.info("Fichero de configuracion cargado")
    except Exception as e:
        logger.critical("Error en cargar o recargar la configuracion")

# Comprobar que se haya ejecutado el comando setup en el servidor
def CheckSetUp(ctx):
    logger.debug("Comprobando estado de setup")
    if not bool(configJson[str(ctx.guild.id)]["setup"]):
        return True

# Obtener el prefijo del servidor en la cual se esta enviando el mensaje a travez de la variable global
def GetPrefix(bot, message):
    guildID = str(message.guild.id)
    logger.debug(f"Recopilando prefix del servidor {guildID}")
    prefix = configJson[guildID]["prefix"]
    return prefix

# Devuelve true si el usuario tiene los roles indicados en la configuracion del servidor
def IsSU():
    async def predicate(ctx):
        guildID = str(ctx.guild.id)
        suRoles = configJson[guildID]["su"]
        if configJson[guildID]["setup"] == 0:
            raise commands.MissingAnyRole(suRoles)
        if any(role.id in suRoles for role in ctx.author.roles):
            return True
        raise commands.MissingAnyRole(suRoles)
    return commands.check(predicate)

# Se llama a esta funcion cuando un servidor no esta registrado en el json
#! Esta funcion recarga la variable de configuracion ya que añade un servidor nuevo
# Por defecto el setup esta en falso para que el usuario tenga que ejecutar el comando
def DefaultServerConfig(guild):
    try:
        # Cnfiguracion por defecto
        configJson[guild] = {
            "setup": 0,
            "prefix": "hs$",
            "su": [],
            "log": 0,
            "ticket": {
                "general": 0,
                "mensaje": "Bienvenido al servidor.",
                "category": 0,
                "miembro": 0,
                "su": [],
                "panels": {}
            }
        }
        with open("botconfig.json", "w", encoding="utf-8") as file:
            dump(configJson, file, indent=4)

        logger.info("Configuracion por defecto creada para el servidor")
        ChargeConfig() # Recarga la configuración
    except Exception as e:
        logger.error(f"Error al guardar la configuracion por defecto: {e}")
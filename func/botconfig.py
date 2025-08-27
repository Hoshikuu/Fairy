from discord.ext import commands

from json import load, dump
from os.path import isfile

from func.logger import get_logger

# Variable que se usa globalmente para poder acceder al contenido del archivo de configuración del bot
configJson = None # Literalmente la cosa mas importante del bot sin esto explota

logger = get_logger(__name__)

def CheckFile():
    """Comprueba que el fichero de configuración este creado
    """
    if isfile("botconfig.json"):
        return
    
    logger.warning("Fichero de configuración no esta creado")
    with open("botconfig.json", "w", encoding="utf-8") as file:
        logger.debug("Creando fichero de configuración")
        file.write("{}")
        logger.info("Fichero de configuración creado")

# TODO: Que se pueda cambiar dinámicamente el nombre del archivo de configuración
def ChargeConfig():
    """Carga la configuración del archivo de botconfig, también recarga el archivo si se llama en ejecución
    """
    try:
        CheckFile()
        global configJson # Para poder modificar la variable

        # Lee el contenido del json y lo carga a la variable
        with open("botconfig.json", "r", encoding="utf-8") as file:
            configJson = load(file)
            logger.info("Fichero de configuración cargado")
    except Exception as e:
        logger.critical("Error en cargar o recargar la configuración")

def CheckSetUp(ctx):
    """Comprueba que este configurado el setup del bot en el servidor

    Args:
        ctx (ctx): Mensaje

    Returns:
        bool: Devuelve True si el bot no esta configurado, sino devuelve False
    """
    logger.debug("Comprobando estado de setup")
    if not bool(configJson[str(ctx.guild.id)]["setup"]):
        return True
    return False

def GetPrefix(bot, message):
    """Obtener el prefix del servidor en la cual se esta enviando el mensaje a traves de la variable global

    Args:
        bot (bot): No se para que sirve en serio, algo para discord
        message (ctx): Mensaje

    Returns:
        str: Devuelve el prefix del servidor del mensaje
    """
    guildID = str(message.guild.id)
    logger.debug(f"Recopilando prefix del servidor {guildID}")
    prefix = configJson[guildID]["prefix"]
    return prefix

def IsSU():
    async def predicate(ctx):
        """Comprueba que sea un super usuario

        Args:
            ctx (ctx): Mensaje

        Raises:
            commands.MissingAnyRole: Falta rol de super usuario

        Returns:
            bool: Devuelve True si no hay un setup y devuelve True si eres super usuario
        """
        guildID = str(ctx.guild.id)
        suRoles = configJson[guildID]["su"]
        if configJson[guildID]["setup"] == 0:
            return True
        if any(role.id in suRoles for role in ctx.author.roles):
            return True
        raise commands.MissingAnyRole(suRoles)
    return commands.check(predicate)

# Se llama a esta función cuando un servidor no esta registrado en el json
#! Esta función recarga la variable de configuración ya que añade un servidor nuevo
# Por defecto el setup esta en falso para que el usuario tenga que ejecutar el comando
# FIXME: Esto es muy ineficiente
def DefaultServerConfig(guild):
    """Añade un servidor con la configuración por defecto

    Args:
        guild (str): El id del servidor que sea crea una nueva configuración
    """
    try:
        # Configuración por defecto
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

        logger.info("Configuración por defecto creada para el servidor")
        ChargeConfig() # Recarga la configuración
    except Exception as e:
        logger.error(f"Error al guardar la configuración por defecto: {e}")
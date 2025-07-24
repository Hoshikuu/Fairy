from func.terminal import now
from json import load, dump
from os.path import isfile

# LA UNICA SOLUCION QUE HE ENCONTRADO PARA RECARGAR EL MALDITO ARCHIVO DE CONFIGURACION ME CAGO EN LA PUTA
configJson = None

# Carga el archivo de configuracion
# Se puede llamar en ejecucion para recargar la variable que contiene el archivo de configuracion
# A futuro no se si generara algun problema pero no encuentro otra solucion
def ChargeConfig():
    if not isfile("botconfig.json"):
        print(f"{now()} EXEP     Fichero de configuración no esta creado.")
        with open("botconfig.json", "w", encoding="utf-8") as file:
            file.write("{}")
            print(f"{now()} INFO     Fichero de configuración creado.")
            
    global configJson
    with open("botconfig.json", "r", encoding="utf-8") as file:
        configJson = load(file)
        print(f"{now()} INFO     Cargando fichero de configuración")

# Obtiene el prefijo del servidor del cual se envia el mensaje
def GetPrefix(bot, message):
    guildID = str(message.guild.id)
    prefix = configJson[guildID]["prefix"]
    print(f"{now()} INFO     Obteniendo prefijo del servidor: {guildID} con prefijo: '{prefix}'.")
    return prefix

# Funcion para crear la configuracion por defecto de un servidor
# Luego se tiene que ejecutar el comando de setup para configurar el bot
def DefaultServerConfig(guild):
    configJson[guild] = {
        "setup": 0,
        "prefix": "hs$",
        "su": []
    }
    with open("botconfig.json", "w") as file:
        dump(configJson, file, indent=4)
    ChargeConfig()

def CheckSetUp(ctx):
    # Prevenir la ejecucion de comandos si no esta configurado el bot.
    if not bool(configJson[str(ctx.guild.id)]["setup"]):
        return True
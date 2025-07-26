# Modulos para obtener variables de entorno
from os import getenv
from dotenv import load_dotenv

# Modulo de funciones
from func.terminal import now

# Obtener el token del bot
def GetToken():
    # Obtener el token del bot
    load_dotenv()
    token = getenv("DISCORD_TOKEN")
    print(f"{now()} INFO     Token establecido.")
    return token
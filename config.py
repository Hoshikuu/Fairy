# Modulos para obtener variables de entorno
from os import getenv
from dotenv import load_dotenv
from func.terminal import now

def GetToken():
    # No mires esto es secreto, alejate de esta zona del codigo te estoy mirando.
    load_dotenv()
    token = getenv("DISCORD_TOKEN")
    print(f"{now()} INFO     Token establecido.")
    return token
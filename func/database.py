# Modulo para manejar la base de datos
from sqlite3 import connect

# Modulos extra
from os.path import isfile

# Modulo de funciones
from func.terminal import printr

# Conecta a la base de datos dependiendo del id del servidor, si no existe lo crea
def DatabaseConnect(guild): # !!: Recuerda siempre pasarle el ctx.guild.id
    if not isfile(f"database/{guild}.db"):
        printr(f"Creando una nueva Base de Datos para {guild}", 2)
        CreateDatabase(guild)

    conn = connect(f"database/{guild}.db")
    return conn

# Crea la tabla principal para almacenar la cantidad de mensajes enviados por usuario y demas
def CreateDatabase(guild):
    conn = connect(f"database/{guild}.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data (
        id INTEGER PRIMARY KEY,
        username TEXT,
        date TEXT,
        messages INTEGER DEFAULT 0,
        voicechat FLOAT DEFAULT 0
    )
    """)
    
    printr(f"Nueva tabla creada para el servidor: {guild}.", 2)
    conn.commit()
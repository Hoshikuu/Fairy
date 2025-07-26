# Modulo para manejar la base de datos
from sqlite3 import connect

# Modulo de funciones
from func.terminal import now

# Conecta a la base de datos dependiendo del id del servidor, si no existe lo crea
def DatabaseConnect(guild): # !!: Recuerda siempre pasarle el ctx.guild.id
    conn = connect(f"database/{guild}.db")
    print(f"{now()} INFO     Conectado a la base de datos del servidor: {guild}.")
    return conn

# Crea la tabla principal para almacenar la cantidad de mensajes enviados por usuario y demas
def CreateDatabase(guild):
    conn = DatabaseConnect(guild)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mensajes (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        cantidad INTEGER DEFAULT 0
    )
    """)
    
    print(f"{now()} WARN     Nueva tabla creada para el servidor: {guild}.")
    conn.commit()
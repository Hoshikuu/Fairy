import sqlite3
from func.terminal import now

# Dependiendo de que servidor el nombre de la base de datos cambia para no filtrar informacion de un servidor en concreto
# Conexiona la base de datos
def DatabaseConnect(guild): # !!: Recuerda siempre pasarle el ctx.guild.id
    conn = sqlite3.connect(f"{guild}.db")
    print(f"{now()} INFO     Conectado a la base de datos del servidor: {guild}.")
    return conn

# Crea la tabla principal para almacenar la cantidad de mensajes enviados por usuario
def CreateDatabase(guild):
    conn = DatabaseConnect(guild)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mensajes (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        cantidad INTEGER DEFAULT 0
    )
    """) # EWWWWWWWWWWWWWW SQL PUTA MIERDA
    
    print(f"{now()} WARN     Nueva tabla creada para el servidor: {guild}.")
    conn.commit()
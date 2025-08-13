# Modulo para manejar la base de datos
from sqlite3 import connect

# Modulos extra
from os.path import isfile

# Modulo de funciones
from func.logger import get_logger

logger = get_logger(__name__)

# Conecta a la base de datos dependiendo del id del servidor, si no existe lo crea
def DatabaseConnect(guild): # !!: Recuerda siempre pasarle el ctx.guild.id
    CreateDatabase(guild)
    try:
        conn = connect(f"database/{guild}.db")
        logger.debug(f"Conectado a la base de datos {guild}.db")
        return conn
    except Exception as e:
        logger.error(f"Error inesperado al conectar con la base de datos {guild}.db: {e}")
    
# Crea la tabla principal para almacenar la cantidad de mensajes enviados por usuario y demas
def CreateDatabase(guild):
    try:
        if isfile(f"database/{guild}.db"):
            logger.debug("Base de datos existe")
            return
        
        logger.warning(f"Creando una nueva Base de Datos para {guild}")
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
        
        logger.warning(f"Nueva tabla creada para el servidor: {guild}.")
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error inesperado en la creacion de una nueva base de datos {guild}.db: {e}")

# Crea la tabla para la ruleta diaria
def CreateRouletteDatabase(guild):
    try:
        conn = DatabaseConnect(guild)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 
            FROM sqlite_master 
            WHERE type='table' AND name='roulette';
        """)
        
        if cursor.fetchone():
            logger.debug("Tabla ya existe")
            conn.close()
            return

        logger.warning(f"Creando una nueva Base de Datos de ruleta para {guild}")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roulette (
            id INTEGER PRIMARY KEY,
            username TEXT,
            number TEXT
        )
        """)
        
        logger.warning(f"Nueva tabla creada para el servidor: {guild}.")
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error inesperado en la creacion de una nueva base de datos {guild}.db: {e}")
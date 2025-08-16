from sqlite3 import connect

from os.path import isfile

from func.logger import get_logger

logger = get_logger(__name__)

# Conecta a la base de datos dependiendo del id del servidor, si no existe lo crea
def DatabaseConnect(guild): #! Recuerda siempre pasar le el ctx.guild.id
    """Conecta a la base de datos del servidor

    Args:
        guild (str): ID del servidor

    Returns:
        sqlite.connection: Conexión a la base de sqlite3
    """
    CreateDatabase(guild)
    try:
        conn = connect(f"database/{guild}.db")
        logger.debug(f"Conectado a la base de datos {guild}.db")
        return conn
    except Exception as e:
        logger.error(f"Error inesperado al conectar con la base de datos {guild}.db: {e}")
    
def CreateDatabase(guild):
    """Crea una base de datos nueva para el servidor
    
    Args:
        guild (str): ID del servidor
    """
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
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roulette (
            id INTEGER PRIMARY KEY,
            username TEXT,
            number TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS economy (
            id INTEGER PRIMARY KEY,
            username TEXT,
            date TEXT,
            money INTEGER DEFAULT 0
        )
        """)
        
        logger.warning(f"Nueva tabla creada para el servidor: {guild}.")
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error inesperado en la creacion de una nueva base de datos {guild}.db: {e}")
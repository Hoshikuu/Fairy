#                                                                    ---------------------------------
#
#                                                                       Script  creado por  Hoshiku
#                                                                       https://github.com/Hoshikuu
#
#                                                                    ---------------------------------

# database.py - V2.0

from sqlite3 import connect, DataError
from os.path import isfile, isdir
from os import mkdir

from func.logger import get_logger

logger = get_logger(__name__)

def create_global_db():
    """Crea la base de datos global si no existe
    """
    
    logger.warning("Creando una nueva Base de Datos Global")
    conn = connect("database/global.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE "token" (
        "id"	TEXT NOT NULL UNIQUE,
        "token"	TEXT UNIQUE,
        PRIMARY KEY("id")
    );
    """)

    conn.commit()
    conn.close()
    logger.info("Base de datos global creada")

def check_file():
    """Comprueba que la base de datos este creada
    """
    if isfile("database/global.db"):
        return
    
    if not isdir("database"):
        logger.warning("Creando nueva carpeta de Database")
        mkdir("database")
    
    create_global_db()
    
def get_global_db(token: str):
    """Consulta el token en la base de datos global

    Args:
        token (str): Token de la configuración del bot

    Raises:
        DataError: Cuando no se encuentre un token en la base de datos

    Returns:
        str: Devuelve la fila del token o None si no existe
    """
    
    check_file()
    try:
        conn = connect("database/global.db")
        logger.debug("Conectado a la base de datos global.db")
        if token != None:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM token WHERE id = ?", (token,))
            data = cursor.fetchone()
            print(data)
            return data
        raise DataError
    
    except DataError as e:
        logger.error(f"No se ha encontrado el token en la base de datos global.db")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al conectar con la base de datos global.db: {e}")
        return None
        
def insert_global_db(id: str, token: str):
    """Inserta un nuevo token en la base de datos global

    Args:
        id (str): ID del token
        token (str): Token de la configuración del bot

    Returns:
        bool: Devuelve True si se ha insertado correctamente, False si ha habido un error
    """
    
    check_file()
    try:
        conn = connect("database/global.db")
        logger.debug("Conectado a la base de datos global.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO token (id, token) VALUES (?, ?)", (id, token))
        conn.commit()
        logger.info(f"Token insertado correctamente en la base de datos global.db")
        return True
    except Exception as e:
        logger.error(f"Error inesperado al insertar el token en la base de datos global.db: {e}")
        return False
    
def update_global_db(id: str, token: str):
    """Actualiza el token en la base de datos global

    Args:
        id (str): ID del token
        token (str): Token de la configuración del bot
    Returns:
        bool: Devuelve True si se ha actualizado correctamente, False si ha habido un error
    """
    
    check_file()
    try:
        conn = connect("database/global.db")
        logger.debug("Conectado a la base de datos global.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE token SET token = ? WHERE id = ?", (token, id))
        conn.commit()
        logger.info(f"Token actualizado correctamente en la base de datos global.db")
        return True
    except Exception as e:
        logger.error(f"Error inesperado al actualizar el token en la base de datos global.db: {e}")
        return False
    

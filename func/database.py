#                                                                    ---------------------------------
#
#                                                                       Script  creado por  Hoshiku
#                                                                       https://github.com/Hoshikuu
#
#                                                                    ---------------------------------

# database.py - V2.0

# Dynamic database management system for multiple configurations

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
        "token"	TEXT NOT NULL UNIQUE,
        "password"	TEXT NOT NULL,
        "data"	TEXT NOT NULL,
        "valid"	TEXT NOT NULL,
        PRIMARY KEY("id")
    );
    """)

    conn.commit()
    conn.close()
    logger.info("Base de datos global creada")

def check_file(id: str = None):
    """Comprobar si existe la base de datos global y la de configuración

    Args:
        id (str, optional): El id de la base de datos de configuración. Defaults to None.
    """
    if id != None and not isfile(f"database/{id}.db"):
        logger.warning(f"No se ha encontrado la base de datos de configuración para el ID {id}, creando una nueva...")
        create_db(id)
    
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
        tuple: Devuelve una tupla con los datos del token si se encuentra, None si no se encuentra
    """
    
    check_file()
    try:
        conn = connect("database/global.db")
        logger.debug("Conectado a la base de datos global.db")
        if token is not None:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM token WHERE token = ?", (token,))
            data = cursor.fetchone()
            if data is not None:
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
    
def create_db(id: str):
    """Crea la base de datos de configuración si no existe

    Args:
        id (str): ID del token
    """
    
    logger.warning(f"Creando una nueva Base de Datos de Configuración para el ID {id}")
    conn = connect(f"database/{id}.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE "config" (
        "id"	INTEGER NOT NULL UNIQUE,
        "setup"	INTEGER NOT NULL DEFAULT 0,
        "prefix"	TEXT NOT NULL DEFAULT 'hs$',
        "log"	TEXT,
        PRIMARY KEY("id")
    );
    """)

    cursor.execute("""
    CREATE TABLE "op" (
        "id"	TEXT NOT NULL UNIQUE,
        "name"	TEXT,
        PRIMARY KEY("id")
    );
    """)

    cursor.execute("""
    CREATE TABLE "ticket" (
        "id"	INTEGER NOT NULL UNIQUE,
        "general"	TEXT NOT NULL,
        "category"	TEXT NOT NULL,
        "member"	TEXT NOT NULL,
        "message"	TEXT NOT NULL DEFAULT 'Welcome',
        PRIMARY KEY("id")
    );
    """)

    cursor.execute("""
    CREATE TABLE "ticket_op" (
        "id"	TEXT NOT NULL UNIQUE,
        "name"	TEXT,
        PRIMARY KEY("id")
    );  
    """)

    cursor.execute("""
    CREATE TABLE "ticket_panels" (
        "id"	TEXT NOT NULL UNIQUE,
        "count"	TEXT NOT NULL,
        "title"	TEXT NOT NULL,
        "description"	TEXT NOT NULL,
        "category"	TEXT NOT NULL,
        "name"	TEXT NOT NULL,
        PRIMARY KEY("id")
    );
    """)

    cursor.execute("""
    CREATE TABLE "data" (
        id INTEGER PRIMARY KEY,
        username TEXT,
        date TEXT,
        messages INTEGER DEFAULT 0,
        voicechat FLOAT DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()
    logger.info(f"Base de datos de configuración creada para {id}")


def select_db(id: str, atribute: str, table: str, what: str, condition: str):    
    """Selecciona datos de la base de datos

    Args:
        id (str): Id de la base de datos
        atribute (str): El campo al que seleccionar, * para todos
        table (str): La tabla de la base de datos
        what (str): Que campo se va a comparar
        condition (str): La condición a comparar

    Returns:
        tuple: Devuelve una tupla con los datos seleccionados, None si no se encuentra
    """

    check_file(id)
    try:
        conn = connect(f"database/{id}.db")
        cursor = conn.cursor()
        cursor.execute(
        f"""
        SELECT {atribute} FROM {table} WHERE {what} = {condition}
        """)
        data = cursor.fetchone()
        conn.close()
        return data
    except Exception as e:
        logger.error(f"Error inesperado al seleccionar datos de la base de datos {id}.db: {e}")
        return None
    
def insert_db(id: str, table: str, values: str, data: tuple):
    """Inserta datos en la base de datos

    Args:
        id (str): Id de la base de datos
        table (str): La tabla de la base de datos
        values (str): Los campos a insertar separados por comas
        data (tuple): Una tupla con los datos a insertar

    Returns:
        bool: Devuelve True si se ha insertado correctamente, False si ha habido un error
    """

    check_file(id)
    try:
        conn = connect(f"database/{id}.db")
        cursor = conn.cursor()
        cursor.execute(
        f"""
        INSERT INTO {table} ({values}) VALUES ({','.join(['?' for _ in values.split(',')])})
        """, data)
        conn.commit()
        conn.close()
        logger.info(f"Datos insertados correctamente en la base de datos {id}.db")
        return True
    except Exception as e:
        logger.error(f"Error inesperado al insertar datos en la base de datos {id}.db: {e}")
        return False
    
def update_db(id: str, table: str, set_field: str, set_value: str, what: str, condition: str):
    """Actualiza datos en la base de datos

    Args:
        id (str): Id de la base de datos
        table (str): La tabla de la base de datos
        set_field (str): El campo a actualizar
        set_value (str): El nuevo valor del campo
        what (str): Que campo se va a comparar
        condition (str): La condición a comparar

    Returns:
        bool: Devuelve True si se ha actualizado correctamente, False si ha habido un error
    """

    check_file(id)
    try:
        conn = connect(f"database/{id}.db")
        cursor = conn.cursor()
        cursor.execute(
        f"""
        UPDATE {table} SET {set_field} = {set_value} WHERE {what} = {condition}
        """)
        conn.commit()
        conn.close()
        logger.info(f"Datos actualizados correctamente en la base de datos {id}.db")
        return True
    except Exception as e:
        logger.error(f"Error inesperado al actualizar datos en la base de datos {id}.db: {e}")
        return False
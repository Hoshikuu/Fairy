from os.path import isdir
from os import mkdir

from func.logger import get_logger

logger = get_logger(__name__)

def CheckDirs():
    if not isdir("csv"):
        logger.warning("Creando nueva carpeta de CSV")
        mkdir("csv")

    if not isdir("database"):
        logger.warning("Creando nueva carpeta de Database")
        mkdir("database")
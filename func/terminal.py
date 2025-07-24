from datetime import datetime
from pytz import timezone

# Funcion que devuelve la fecha y hora de ahora mismo para el debug de la terminal o cualquier otra chorrada
def now():
    return datetime.now(timezone("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S")
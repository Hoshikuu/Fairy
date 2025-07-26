# Modulos para obtener el tiempo
from datetime import datetime
from pytz import timezone

# TODO: Aqui iran las funcione que hagan cosas en la terminal 

# Funcion para saber la fecha y hora actual de Madrid
def now():
    return datetime.now(timezone("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S")
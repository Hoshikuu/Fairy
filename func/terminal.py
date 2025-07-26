# Modulos para obtener el tiempo
from datetime import datetime
from pytz import timezone

# TODO: Aqui iran las funcione que hagan cosas en la terminal 

# TODO: Añadir el Rich a la terminal para un mejor output
# --------------------
# 1 -> INFO -> Information
# 2 -> WARN -> Warning
# 3 -> ERRO -> Error
# 4 -> EXEP -> Exeption
# --------------------

# Funcion para saber la fecha y hora actual de Madrid
def now():
    return datetime.now(timezone("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S")

def printr(text, type):
    match type:
        case 1:
            print(f"{now()} INFO     {text}")
        case 2:
            print(f"{now()} WARN     {text}")
        case 3:
            print(f"{now()} ERRO     {text}")
        case 4:
            print(f"{now()} EXEP     {text}")
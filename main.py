# Puto modulo para hacer bots me come los cojones
import discord
from discord.ext import commands

# Modulos para obtener variables de entorno
from os import getenv
from dotenv import load_dotenv

# Modulos adicionales
import sqlite3
import csv
import json
from datetime import datetime
from pytz import timezone
from os.path import isfile

# TODO: Algo de rich print para que haga prints en colores en la terminal en teoria es un momento el modulo solo habra que cambiar todo y es una pereza
# ---------------------------------------------------------------------------------------
# 
# INFO-> Information
# WARN-> Warning
# ERRO-> Error
# EXEP -> Exeption
# 
# ---------------------------------------------------------------------------------------

# Funcion que devuelve la fecha y hora de ahora mismo para el debug de la terminal o cualquier otra chorrada
def now():
    return datetime.now(timezone("Europe/Madrid")).strftime("%Y-%m-%d %H:%M:%S")

# No mires esto es secreto, alejate de esta zona del codigo te estoy mirando.
load_dotenv()
TOKEN = getenv("DISCORD_TOKEN")
print(f"{now()} INFO     Token establecido.")

# LA UNICA SOLUCION QUE HE ENCONTRADO PARA RECARGAR EL MALDITO ARCHIVO DE CONFIGURACION ME CAGO EN LA PUTA
configJson = None

# Carga el archivo de configuracion
# Se puede llamar en ejecucion para recargar la variable que contiene el archivo de configuracion
# A futuro no se si generara algun problema pero no encuentro otra solucion
def ChargeConfig():
    global configJson
    with open("botconfig.json", "r", encoding="utf-8") as file:
        configJson = json.load(file)

# Cargo la informacion ya que de antes no la pude cargar porque la funcion aun no estaba definida
ChargeConfig()
print(f"{now()} INFO     Fichero de configuración cargado.")

# Obtiene el prefijo del servidor del cual se envia el mensaje
def GetPrefix(bot, message):
    guildID = str(message.guild.id)
    prefix = configJson[guildID]["prefix"]
    print(f"{now()} INFO     Obteniendo prefijo del servidor: {guildID} con prefijo: '{prefix}'.")
    return prefix

# ME DA PALO HACER QUE USE LOS PERMISOS ESPECIFICOS ASI QUE LE DOY TODOS LOS PERMISOS
# Permisos del bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=GetPrefix, intents=intents) # TODO: Cambia el sufijo porfavor que me cuesta escribirlo
print(f"{now()} INFO     Permisos del Bot establecidos.")

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

# Para mostrar en que servidores esta sirviendo el bot
# NO LO VA A USAR NADIE PORQUE HAGO ESTO
# Mensaje de inicio
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"{now()} INFO     Sincronizados {len(synced)} comandos.")
    except Exception as e:
        print(f"{now()} ERRO     Error al sincronizar comandos: {e}.")
        
    print(f"{now()} INFO     Bot conectado como {bot.user}.")
    
    for guild in bot.guilds:
        print(f"{now()} INFO     Conectado al servidor: {guild.name} con id: {guild.id}.")
        
    print(f"{now()} INFO     BOT listo para usarse.")

# Registrar cada mensaje de cada usuario exeptuando bots
@bot.event
async def on_message(message):
    if message.author.bot: # Se salta si es un BOT
        print(f"{now()} WARN     Mensaje es un BOT.")
        return
    
    # Guarda los datos del mensaje en una variable
    userID = message.author.id
    guildID = message.guild.id
    username = str(message.author)
    
    if not isfile(f"{guildID}.db"):
        print(f"{now()} WARN     Creando una nueva Base de Datos para {guildID}")
        CreateDatabase(guildID)
    
    conn = DatabaseConnect(guildID)
    cursor = conn.cursor()
    
    # Seleccionar los datos si no existe devuelve vacio
    cursor.execute("SELECT cantidad FROM mensajes WHERE user_id = ?", (userID,))
    data = cursor.fetchone()
    print(f"{now()} INFO     Datos obtenidos.")
    
    # PUTA MIERDA DE SQL
    if data: # Actualizar el contador de mensajes
        newCount = data[0] + 1
        cursor.execute("UPDATE mensajes SET cantidad = ? WHERE user_id = ?", (newCount, userID))
    else: # Añadir un nuevo registro
        cursor.execute("INSERT INTO mensajes (user_id, username, cantidad) VALUES (?, ?, ?)", (userID, username, 1))

    conn.commit()
    
    print(f"{now()} INFO     Contador actualizado.")
    await bot.process_commands(message)

# TODO: Deberia pensar en un nombre mejor para este comando no me gusta esto
# Comando para mostrar el contador de mensajes de cada usuario
@bot.hybrid_command(name="count", description="Muestra el contador de mensajes.")
@commands.has_any_role("Miembro") # Recuerda que tambien se puede usar ID de roles para mas seguridad por si se cambia el nombre
async def count(ctx):
    conn = DatabaseConnect(ctx.guild.id)
    cursor = conn.cursor()
    cursor.execute("SELECT username, cantidad FROM mensajes ORDER BY cantidad DESC")
    datos = cursor.fetchall() # Obtiene los datos de cantidad de mensajes de todos los usuarios
    print(f"{now()} INFO     Datos obtenidos.")
    
    # UFFFF EMBEDS QUE BONITOS POR DIOS
    embed = discord.Embed(
        title="Contador Mensajes",
        description="",
        color=discord.Color.blue()  # HEX: discord.Color.from_rgb(0,0,0)
    )
    # Muestra el usuario y la cantidad de mensajes enviado en una pantalla de descripcion
    # TODO: Pa futuro separarlos en varias paginas para mejor legibilidad
    text = ""
    for i, (username, cantidad) in enumerate(datos, start=1):
        text += f"**{i}** {username} — **{cantidad} mensajes**\n"
    embed.description = text
    print(f"{now()} INFO     Mostrando datos del contador en el Discord.")
    await ctx.send(embed=embed, reference=ctx.message)

# TODO: Esta funcion se puede automatizar mas con un excel de drive de google (Buscar como hacerlo)
# Explicacion sencilla es basicamente, descargar una plantilla del excel, introducir los datos del csv y volver a subirlo al drive, eso o enviarte el excel por chat
# Con todas las estadisticas
# Funcion para exportar los datos actuales a CSV y enviarlas por chat
@bot.hybrid_command(name="export", description="Exporta en un CSV el contador de mensajes.")
@commands.has_any_role("Miembro") # Recuerda que tambien se puede usar ID de roles para mas seguridad por si se cambia el nombre
async def export(ctx):
    conn = DatabaseConnect(ctx.guild.id)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, cantidad FROM mensajes ORDER BY cantidad DESC")
    datos = cursor.fetchall() # Obtiene todos los datos
    print(f"{now()} INFO     Datos obtenidos.")
    
    # Chapuza que hice pero funciona, ni se si sera sostenible a futuro xd
    csvData = []
    for i, (userID, username, count) in enumerate(datos, start=1):
        csvData.append([userID, username, count])
    print(f"{now()} INFO     Datos en CSV creados.")
        
    # Guarda el archivo localmente en CSV
    with open(f"{ctx.guild.id}Export.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(datos)
    print(f"{now()} INFO     Archivo CSV creado y listo.")    
    
    # Te envia el CSV
    await ctx.send("Exporting message count:", file=discord.File(f"{ctx.guild.id}Export.csv"), reference=ctx.message)

# Funcion para cambiar el prefijo en la configuracion del bot
# La funcion pide un argumento, el prefijo nuevo
@bot.hybrid_command(name="setprefix", description="Establece el prefijo del bot.")
@commands.has_any_role("Miembro")
async def setprefix(ctx, prefix):
    configJson[str(ctx.guild.id)]["prefix"] = prefix # El nuevo prefijo
    with open("botconfig.json", "w") as f:
        json.dump(configJson, f, indent=4)
        
    ChargeConfig() # Recarga la configuracion del bot
    print(f"{now()} INFO     Fichero de configuracion recargado.")
    
    await ctx.send(f"Prefijo cambiado a: `{prefix}`", reference=ctx.message)

# Esto infica si la funcion da error ejecutar esto
@export.error
@count.error
@setprefix.error
# Error de permisos, Falta de permisos
async def permission_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
        embed = discord.Embed(
            title="Permiso Denegado",
            description="No tienes permisos para ejecutar este comando.",
            color=discord.Color.red()  # HEX: discord.Color.from_rgb(0,0,0)
        )
        print(f"{now()} EXEP     Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando.")
        await ctx.send(embed=embed, reference=ctx.message)

# Informacion basica del bot
#* Esto hay que tenerlo en cuenta, Este comando Hybrido funciona si usaras comandos de prefijo pero tambien te los añade en el command tree asi que son utiles para no repetir mucho codigo
@bot.hybrid_command(name="info", description="Muestra la información básica del bot")
async def info(ctx: commands.Context):
    embed = discord.Embed(
        title="HoyoStars",
        description="Un bot privado para el servidor HoyoStars.",
        color=discord.Color.blue()
    )

    # Para obtener el usuario correctamente en ambos casos
    user = ctx.author if ctx.author else ctx.user
    embed.set_author(name=user.name, icon_url=user.avatar.url)

    embed.add_field(name="Ping", value=f"{round(ctx.bot.latency * 1000)}ms", inline=False)
    embed.add_field(name="Creador", value="yhoshiku", inline=True)
    embed.set_footer(text="Gracias por usarme ❤️")

    await ctx.send(embed=embed)
    
# Para ejecutar el bot, amego tu tener cegarro?
if __name__ == "__main__":
    print(f"{now()} INFO     Iniciando Bot HoyoStars.")
    bot.run(TOKEN)
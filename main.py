# Puto modulo para hacer bots me come los cojones
import discord
from discord.ext import commands

# Modulos para obtener variables de entorno
from os import getenv
from dotenv import load_dotenv

# Modulos adicionales
import sqlite3
import csv

# ---------------------------------------------------------------------------------------

# No mires esto es secreto, alejate de esta zona del codigo te estoy mirando.
load_dotenv()
TOKEN = getenv("DISCORD_TOKEN")

# ME DA PALO HACER QUE USE LOS PERMISOS ESPECIFICOS ASI QUE LE DOY TODOS LOS PERMISOS
# Permisos del bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="hs$", intents=intents) # TODO: Cambia el sufijo porfavor que me cuesta escribirlo

# Dependiendo de que servidor el nombre de la base de datos cambia para no filtrar informacion de un servidor en concreto
# Conexiona la base de datos
def DatabaseConnect(guild): # !!: Recuerda siempre pasarle el ctx.guild.id
    conn = sqlite3.connect(f"{guild}.db")
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
    conn.commit()

# Para mostrar en que servidores esta sirviendo el bot
# NO LO VA A USAR NADIE PORQUE HAGO ESTO
# Mensaje de inicio
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    for guild in bot.guilds:
        print(f"Conectado al servidor: {guild.name} con id: {guild.id}")

# Registrar cada mensaje de cada usuario exeptuando bots
@bot.event
async def on_message(message):
    if message.author.bot: # Se salta si es un BOT
        return
    
    # Guarda el usuario en una variable
    user_id = message.author.id
    username = str(message.author)
    
    CreateDatabase(message.guild.id)
    
    conn = DatabaseConnect(message.guild.id)
    cursor = conn.cursor()
    
    # Seleccionar los datos si no existe devuelve vacio
    cursor.execute("SELECT cantidad FROM mensajes WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    
    # PUTA MIERDA DE SQL
    if data: # Actualizar el contador de mensajes
        nueva_cantidad = data[0] + 1
        cursor.execute("UPDATE mensajes SET cantidad = ? WHERE user_id = ?", (nueva_cantidad, user_id))
    else: # Añadir un nuevo registro
        cursor.execute("INSERT INTO mensajes (user_id, username, cantidad) VALUES (?, ?, ?)", (user_id, username, 1))

    conn.commit()

    await bot.process_commands(message)

# TODO: Deberia pensar en un nombre mejor para este comando no me gusta esto
# Comando para mostrar el contador de mensajes de cada usuario
@bot.command()
@commands.has_any_role("Miembro") # Recuerda que tambien se puede usar ID de roles para mas seguridad por si se cambia el nombre
async def count(ctx):
    conn = DatabaseConnect(ctx.guild.id)
    cursor = conn.cursor()
    cursor.execute("SELECT username, cantidad FROM mensajes ORDER BY cantidad DESC")
    datos = cursor.fetchall() # Obtiene los datos de cantidad de mensajes de todos los usuarios
    
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
    await ctx.send(embed=embed, reference=ctx.message)

# TODO: Esta funcion se puede automatizar mas con un excel de drive de google (Buscar como hacerlo)
# Explicacion sencilla es basicamente, descargar una plantilla del excel, introducir los datos del csv y volver a subirlo al drive, eso o enviarte el excel por chat
# Con todas las estadisticas
# Funcion para exportar los datos actuales a CSV y enviarlas por chat
@bot.command()
@commands.has_any_role("Miembro") # Recuerda que tambien se puede usar ID de roles para mas seguridad por si se cambia el nombre
async def export(ctx):
    conn = DatabaseConnect(ctx.guild.id)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, cantidad FROM mensajes ORDER BY cantidad DESC")
    datos = cursor.fetchall() # Obtiene todos los datos
    
    # Chapuza que hice pero funciona, ni se si sera sostenible a futuro xd
    csvData = []
    for i, (user_id, username, cantidad) in enumerate(datos, start=1):
        csvData.append([user_id, username, cantidad])
        
    # Deberia de meter mas DEBUG de por medio no tira nada el bot
    # Guarda el archivo localmente en CSV
    with open(f"{ctx.guild.id}Export.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(datos)
        
    # Te envia el CSV
    await ctx.send("Exporting message count:", file=discord.File(f"{ctx.guild.id}Export.csv"), reference=ctx.message)

# Esto infica si la funcion da error ejecutar esto
@export.error
@count.error
# Error de permisos, Falta de permisos
async def permission_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
        embed = discord.Embed(
            title="Permiso Denegado",
            description="No tienes permisos para ejecutar este comando.",
            color=discord.Color.red()  # HEX: discord.Color.from_rgb(0,0,0)
        )
        await ctx.send(embed=embed, reference=ctx.message)

# Comando para mostrar la informacion basica del bot
@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title="HoyoStars",
        description="Un bot privado para el servidor HoyoStars.",
        color=discord.Color.blue()  # HEX: discord.Color.from_rgb(0,0,0)
    )
    embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
    embed.add_field(name="Ping", value=f"{round(bot.latency*1000)}ms", inline=False)
    embed.add_field(name="Creador", value="yhoshiku", inline=True) # Si, Soy yo.
    embed.set_footer(text="Gracias por usarme ❤️")

    await ctx.send(embed=embed, reference=ctx.message)

# Para ejecutar el bot, amego tu tener cegarro?
if __name__ == "__main__":
    bot.run(TOKEN)
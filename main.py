import discord
from discord.ext import commands
from os import getenv
from dotenv import load_dotenv
import sqlite3
import csv

# TOKEN
load_dotenv()
TOKEN = getenv("DISCORD_TOKEN")

# Permisos del bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="hs$", intents=intents)

# Conexiona la base de datos
def DatabaseConnect():
    conn = sqlite3.connect("hoyostars.db")
    return conn

# Crea la tabla principal para almacenar la cantidad de mensajes enviados por usuario
def CreateDatabase():
    conn = DatabaseConnect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mensajes (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        cantidad INTEGER DEFAULT 0
    )
    """)
    conn.commit()

# Mensaje de inicio
@bot.event
async def on_ready():
    CreateDatabase()
    print(f"[!] Bot listo y logueado como {bot.user}")

# Registrar cada mensaje de cada usuario exeptuando bots
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    user_id = message.author.id
    username = str(message.author)
    
    conn = DatabaseConnect()
    cursor = conn.cursor()
    
    cursor.execute("SELECT cantidad FROM mensajes WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    
    if data:
        nueva_cantidad = data[0] + 1
        cursor.execute("UPDATE mensajes SET cantidad = ? WHERE user_id = ?", (nueva_cantidad, user_id))
    else:
        cursor.execute("INSERT INTO mensajes (user_id, username, cantidad) VALUES (?, ?, ?)", (user_id, username, 1))

    conn.commit()

    await bot.process_commands(message)

# Comando para mostrar el contador de mensajes de cada usuario
@bot.command()
async def count(ctx):
    conn = DatabaseConnect()
    cursor = conn.cursor()
    cursor.execute("SELECT username, cantidad FROM mensajes ORDER BY cantidad DESC")
    datos = cursor.fetchall()
    
    
    embed = discord.Embed(
        title="Contador Mensajes",
        description="",
        color=discord.Color.blue()  # HEX: discord.Color.from_rgb(0,0,0)
    )
    text = ""
    for i, (username, cantidad) in enumerate(datos, start=1):
        text += f"**{i}** {username} — **{cantidad} mensajes**\n"
    embed.description = text
    await ctx.send(embed=embed)
    
@bot.command()
async def export(ctx):
    conn = DatabaseConnect()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, cantidad FROM mensajes ORDER BY cantidad DESC")
    datos = cursor.fetchall()
    
    csvData = []
    for i, (user_id, username, cantidad) in enumerate(datos, start=1):
        csvData.append([user_id, username, cantidad])
        
    print(csvData)
    with open("csvExport.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(datos)
        
    await ctx.send("Export:", file=discord.File("csvExport.csv"))

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
    embed.add_field(name="Creador", value="yhoshiku", inline=True)
    embed.set_footer(text="Gracias por usarme ❤️")

    await ctx.send(embed=embed)

#
bot.run(TOKEN)
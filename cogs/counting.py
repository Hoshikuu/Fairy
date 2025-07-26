# Modulo de discord
import discord
from discord.ext import commands

# Para manejar el CSV
from csv import writer as csvwriter

# Modulo de funciones
from func.botconfig import CheckSetUp
from func.terminal import now
from func.database import DatabaseConnect

# Comandos relacionados a la cuenta de mensjaes
class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # TODO: Deberia pensar en un nombre mejor para este comando no me gusta esto
    # Comando para mostrar el contador de mensajes de cada usuario
    @commands.hybrid_command(name="count", description="Muestra el contador de mensajes.")
    @commands.has_any_role("Miembro") # Recuerda que tambien se puede usar ID de roles para mas seguridad por si se cambia el nombre
    async def count(self, ctx):
        # Prevenir la ejecucion de comandos si no esta configurado el bot.
        if CheckSetUp(ctx):
            await ctx.send("Porfavor use el comando /setup o hs$setup, antes de ejecutar ningun comando.", reference=ctx.message)
            return
        
        conn = DatabaseConnect(ctx.guild.id)
        cursor = conn.cursor()
        cursor.execute("SELECT username, cantidad FROM mensajes ORDER BY cantidad DESC")
        datos = cursor.fetchall() # Obtiene los datos de cantidad de mensajes de todos los usuarios
        print(f"{now()} INFO     Datos de la base de datos obtenidos.")
        
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
    # TODO: Idea de antes rechazada muy dificil poco efectivo no se guardan las decoraciones del excel aqui va otra idea
    # En el Excel manualmente crear una nueva hoja duplicado de la plantilla renomrarla a LimpiezaHoy o cualquier otra cosa pasarle
    # El nombre al comando y del comando hace lo mismo pero descarga el excel en la hoja asignada inserta los datos del csv tambien hay que
    # Añadir otras cosas como fecha de union, horas en vc y demas introducirlas directamente a la hoja del excel y que el excel se encargue de calcular el porcentaje
    # Funcion para exportar los datos actuales a CSV y enviarlas por chat (Actual) cambia a futuro
    @commands.hybrid_command(name="export", description="Exporta en un CSV el contador de mensajes.")
    @commands.has_any_role("Miembro") # Recuerda que tambien se puede usar ID de roles para mas seguridad por si se cambia el nombre
    async def export(self, ctx):
        # Prevenir la ejecucion de comandos si no esta configurado el bot.
        if CheckSetUp(ctx):
            await ctx.send("Porfavor use el comando /setup o hs$setup, antes de ejecutar ningun comando.", reference=ctx.message)
            return
        
        conn = DatabaseConnect(ctx.guild.id)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, cantidad FROM mensajes ORDER BY cantidad DESC")
        datos = cursor.fetchall() # Obtiene todos los datos
        print(f"{now()} INFO     Datos de la base de datos obtenidos.")
        
        # Lo guarda en un CSV
        csvData = []
        for i, (userID, username, count) in enumerate(datos, start=1):
            csvData.append([userID, username, count])
        print(f"{now()} INFO     Datos en CSV creados.")
            
        # Guarda el archivo localmente en CSV
        with open(f"csv/export-{ctx.guild.id}.csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csvwriter(file)
            writer.writerows(datos)
        print(f"{now()} INFO     Archivo CSV creado y listo.")    
        
        # Te envia el CSV
        await ctx.send("Exporting message count:", file=discord.File(f"csv/export-{ctx.guild.id}.csv"), reference=ctx.message)

    # Esto indica si la funcion da error ejecutar esto
    @export.error
    @count.error
    # Error de permisos, Falta de permisos
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
            embed = discord.Embed(
                title="Permiso Denegado",
                description="No tienes permisos para ejecutar este comando.",
                color=discord.Color.red()  # HEX: discord.Color.from_rgb(0,0,0)
            )
            print(f"{now()} EXEP     Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando.")
            await ctx.send(embed=embed, reference=ctx.message)

# Autorun
async def setup(bot):
    await bot.add_cog(Counting(bot))
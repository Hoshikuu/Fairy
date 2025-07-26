# Modulo de discord
import discord
from discord.ext import commands

from csv import writer as csvwriter

from func.database import DatabaseConnect
from func.botconfig import CheckSetUp, IsSU
from func.terminal import printr

# Template for cog
class Output(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # TODO: Esta funcion se puede automatizar mas con un excel de drive de google (Buscar como hacerlo)
    # Explicacion sencilla es basicamente, descargar una plantilla del excel, introducir los datos del csv y volver a subirlo al drive, eso o enviarte el excel por chat
    # Con todas las estadisticas
    # TODO: Idea de antes rechazada muy dificil poco efectivo no se guardan las decoraciones del excel aqui va otra idea
    # En el Excel manualmente crear una nueva hoja duplicado de la plantilla renomrarla a LimpiezaHoy o cualquier otra cosa pasarle
    # El nombre al comando y del comando hace lo mismo pero descarga el excel en la hoja asignada inserta los datos del csv tambien hay que
    # Añadir otras cosas como fecha de union, horas en vc y demas introducirlas directamente a la hoja del excel y que el excel se encargue de calcular el porcentaje
    # Funcion para exportar los datos actuales a CSV y enviarlas por chat (Actual) cambia a futuro
    @commands.hybrid_command(name="export", description="Exporta en un CSV el contador de mensajes.")
    @IsSU() # Funcion para comprobar si el usuario tiene el de super usuario
    async def export(self, ctx):
        # Prevenir la ejecucion de comandos si no esta configurado el bot.
        if CheckSetUp(ctx):
            await ctx.send("Porfavor use el comando /setup o hs$setup, antes de ejecutar ningun comando.", reference=ctx.message)
            return
        
        conn = DatabaseConnect(ctx.guild.id)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, date, messages, voicechat FROM data ORDER BY messages DESC")
        datos = cursor.fetchall() # Obtiene todos los datos
        
        # Lo guarda en un CSV
        csvData = []
        for i, (userID, username, date, messages, voicechat) in enumerate(datos, start=1):
            csvData.append([userID, date, voicechat, messages, username])
        printr(f"Datos en CSV creados.", 1)
            
        # Guarda el archivo localmente en CSV
        with open(f"csv/export-{ctx.guild.id}.csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csvwriter(file)
            writer.writerows(datos)
        printr(f"Archivo CSV creado y listo.", 1)
        
        # Te envia el CSV
        await ctx.send("Exporting message count:", file=discord.File(f"csv/export-{ctx.guild.id}.csv"), reference=ctx.message)

    # Esto indica si la funcion da error ejecutar esto
    @export.error
    # Error de permisos, Falta de permisos
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
            embed = discord.Embed(
                title="Permiso Denegado",
                description="No tienes permisos para ejecutar este comando.",
                color=discord.Color.red()  # HEX: discord.Color.from_rgb(0,0,0)
            )
            printr(f"Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando.", 4)
            await ctx.send(embed=embed, reference=ctx.message)

# Autorun
async def setup(bot):
    await bot.add_cog(Output(bot))
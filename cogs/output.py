# Modulo de discord
from discord import Color
from discord.ext import commands

from csv import writer as csvwriter

import gspread
import csv

from func.database import DatabaseConnect
from func.botconfig import CheckSetUp, IsSU
from func.terminal import printr

from templates.embeds import SimpleEmbed

# Template for cog
class Output(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="export", description="Exporta los datos en un excel compartido.")
    @IsSU() # Funcion para comprobar si el usuario tiene el de super usuario
    async def export(self, ctx, excel, sheet):
        # Prevenir la ejecucion de comandos si no esta configurado el bot.
        if CheckSetUp(ctx):
            await ctx.send("Porfavor use el comando /setup o hs$setup, antes de ejecutar ningún comando.", reference=ctx.message)
            return
        
        conn = DatabaseConnect(str(ctx.guild.id))
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, date, messages, voicechat FROM data ORDER BY messages DESC")
        datos = cursor.fetchall() # Obtiene todos los datos
        
        try:
            # Lo guarda en un CSV
            csvData = []
            for i, (userID, username, date, messages, voicechat) in enumerate(datos, start=1):
                csvData.append([userID, username, date, messages, f"{round(voicechat, 2):.2f}".replace(".", ",")])
            printr(f"Datos exportados a un CSV local correctamente.", 1)
        except Exception:
            printr(f"Datos no se pudieron exportar en un CSV local.", 4)
            return
        
        try:
            # Guarda el archivo localmente en CSV
            with open(f"csv/export-{ctx.guild.id}.csv", mode="w", newline="", encoding="utf-8") as file:
                writer = csvwriter(file, delimiter=";")
                writer.writerows(csvData)
            printr(f"CSV local guardado correctamente en ./csv/export-{ctx.guild.id}.csv.", 1)
        except Exception:
            printr(f"CSV local no se pudo guardar en ./csv/export-{ctx.guild.id}.csv.", 4)
            return
        
        try:
            gc = gspread.service_account(filename="credentials.json")
            printr("Credenciales cargadas correctamente, entrando con el usuario.", 1)
        except Exception:
            printr("Credenciales del usuario fallaron en cargarse.", 4)
            return
        
        try:
            spreadsheet = gc.open(excel)
            worksheet = spreadsheet.worksheet(sheet)
            printr(f"Abriendo el excel {excel} en la hoja {sheet}.", 1)
        except Exception:
            printr(f"No se pudo abrir el excel {excel} en la hoja {sheet}.", 4)
            return
        
        try:
            user, date, messages, voicechat = [], [], [], []
            with open(f"csv/export-{ctx.guild.id}.csv", "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter=";")
                for row in reader:
                    user.append([row[1]])
                    date.append([row[2]])
                    messages.append([row[3]])
                    voicechat.append([row[4]])
            printr("Datos del CSV local leidos satisfactoriamente.", 1)
            worksheet.update(date, f"A2:A{2 + len(date) - 1}")
            worksheet.update(voicechat, f"B2:B{2 + len(voicechat) - 1}")
            worksheet.update(messages, f"C2:C{2 + len(messages) - 1}")
            worksheet.update(user, f"F2:F{2 + len(user) - 1}")
            printr("Datos insertados en el Excel satisfactoriamente.", 1)
        except:
            printr("Ocurrio un error inesperado en el proceso.", 4)
        printr(f"Datos exportados correctamente al Excel: {worksheet.url}", 1)
        
        # Te envia el link con el Excel
        embed = SimpleEmbed("Exportación de datos", "Los datos de usuarios se han exportado correctamente al Google Sheets. Se procederá a eliminar los datos antiguos.", Color.brand_green())
        await ctx.send(f"{worksheet.url}", embed=embed, reference=ctx.message)
    
        cursor.execute("DELETE FROM data;")
        conn.commit()
        printr("Datos antiguos eliminados de la base de datos.", 1)

    # Esto indica si la funcion da error ejecutar esto
    @export.error
    # Error de permisos, Falta de permisos
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
            printr(f"Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando.", 3)
            embed = SimpleEmbed("Permiso Denegado", "No tienes permisos para ejecutar este comando.", Color.red())
            await ctx.send(embed=embed, reference=ctx.message)

# Autorun
async def setup(bot):
    await bot.add_cog(Output(bot))
from discord import Color
from discord.ext import commands

from csv import writer as csvwriter, reader as csvreader
from gspread import service_account

from backup.database import DatabaseConnect
from func.botconfig import CheckSetUp, IsSU
from func.logger import get_logger
from models.embeds import SimpleEmbed

logger = get_logger(__name__)

class Admin(commands.Cog):
    """Comandos de administración para el bot

    Args:
        commands (Cog): Cog
    """
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="export", description="Exporta los datos en un excel compartido.")
    @IsSU() # Función para comprobar si el usuario tiene el de super usuario
    async def export(self, ctx, excel, sheet):
        """Exportar los datos de mensajes a Excel con una plantilla predefinida

        Args:
            ctx (ctx): Mensaje
            excel (str): Nombre del excel al que insertar los datos
            sheet (str): Hoja de datos del excel al que insertar los datos
        """
        # Prevenir la ejecución de comandos si no esta configurado el bot.
        if CheckSetUp(ctx):
            await ctx.send("Por favor use el comando /setup o hs$setup, antes de ejecutar ningún comando.", reference=ctx.message)
            return
        
        if excel == None or sheet == None:
            await ctx.send(embed=SimpleEmbed("Error", "Por favor introduzca los argumentos para ejecutar el comando\nNombre del Excel + Hoja del Excel", Color.red()), reference=ctx.message)
            return


        message = await ctx.send(embed=SimpleEmbed("Conectando", "Conectando a la base de datos", Color.red()), reference=ctx.message)

        conn = DatabaseConnect(str(ctx.guild.id))
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, date, messages, voicechat FROM data ORDER BY messages DESC")
        datos = cursor.fetchall() # Obtiene todos los datos
        
        try:
            await message.edit(embed=SimpleEmbed("Exportando", "Exportando los datos a CSV", Color.red()))
            # Lo guarda en un CSV
            csvData = []
            for i, (userID, username, date, messages, voicechat) in enumerate(datos, start=1):
                csvData.append([userID, username, date, messages, f"{round(voicechat, 2):.2f}".replace(".", ",")])
            logger.info("Datos exportados a un CSV local correctamente")
        except Exception as e:
            logger.error(f"Datos no se pudieron exportar en un CSV local: {e}")
            return
        
        try:
            await message.edit(embed=SimpleEmbed("Guardando", "Guardando el archivo CSV", Color.red()))
            # Guarda el archivo localmente en CSV
            with open(f"csv/export-{ctx.guild.id}.csv", mode="w", newline="", encoding="utf-8") as file:
                writer = csvwriter(file, delimiter=";")
                writer.writerows(csvData)
            logger.info(f"CSV local guardado correctamente en ./csv/export-{ctx.guild.id}.csv")
        except Exception as e:
            logger.error(f"CSV local no se pudo guardar en ./csv/export-{ctx.guild.id}.csv: {e}")
            return
        
        try:
            await message.edit(embed=SimpleEmbed("Conectando", "Conectando usuario al servicio de Google", Color.red()))
            gc = service_account(filename="credentials.json")
            logger.info("Credenciales cargadas correctamente, entrando con el usuario")
        except Exception as e:
            logger.error(f"Credenciales del usuario fallaron en cargarse: {e}")
            return
        
        try:
            await message.edit(embed=SimpleEmbed("Abriendo", "Abriendo el Excel en la hoja", Color.red()))
            spreadsheet = gc.open(excel)
            worksheet = spreadsheet.worksheet(sheet)
            logger.info(f"Abriendo el excel {excel} en la hoja {sheet}.")
        except Exception as e:
            logger.error(f"No se pudo abrir el excel {excel} en la hoja {sheet}: {e}")
            return
        
        try:
            await message.edit(embed=SimpleEmbed("Escribiendo", "Escribiendo los datos en el Excel", Color.red()))
            user, date, messages, voicechat = [], [], [], []
            with open(f"csv/export-{ctx.guild.id}.csv", "r", encoding="utf-8") as f:
                reader = csvreader(f, delimiter=";")
                for row in reader:
                    user.append([row[1]])
                    date.append([row[2]])
                    messages.append([row[3]])
                    voicechat.append([row[4]])
            logger.info("Datos del CSV local leídos satisfactoriamente")
            worksheet.update(date, f"A2:A{2 + len(date) - 1}")
            worksheet.update(voicechat, f"B2:B{2 + len(voicechat) - 1}")
            worksheet.update(messages, f"C2:C{2 + len(messages) - 1}")
            worksheet.update(user, f"F2:F{2 + len(user) - 1}")
            logger.info("Datos insertados en el Excel satisfactoriamente")
        except Exception as e:
            logger.error(f"Ocurrió un error inesperado en el proceso: {e}")
        logger.info(f"Datos exportados correctamente al Excel: {worksheet.url}")
        
        try:
            # Te envía el link con el Excel
            embed = SimpleEmbed("Exportación de datos", "Los datos de usuarios se han exportado correctamente al Google Sheets. Se procederá a eliminar los datos antiguos.", Color.brand_green())
            await message.edit(content=f"{worksheet.url}", embed=embed)
        except Exception as e:
            logger.error(f"Error inesperado al enviar el mensaje resultado: {e}")
    
        cursor.execute("DELETE FROM data;")
        conn.commit()
        logger.warning("Datos antiguos eliminados de la base de datos")

    # Esto indica si la función da error ejecutar esto
    @export.error
    # Error de permisos, Falta de permisos
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
            logger.error(f"Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando")
            embed = SimpleEmbed("Permiso Denegado", "No tienes permisos para ejecutar este comando.", Color.red())
            await ctx.send(embed=embed, reference=ctx.message)
    
    # TODO: Comando purge (eliminar cierta cantidad de mensajes en el canal)

# Auto run
async def setup(bot):
    await bot.add_cog(Admin(bot))
from discord import Color
from discord.ext import commands

from json import dump

from func.botconfig import configJson, ChargeConfig, CheckSetUp, IsSU
from func.logger import get_logger
from models.views import PanelView
from models.embeds import SimpleEmbed

logger = get_logger(__name__)

class Ticket(commands.Cog):
    """Comandos para manejar tickets

    Args:
        commands (Cog): Cog
    """
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        # Carga las views de los mensajes ya enviados
        try:
            for guild in self.bot.guilds:
                panels = configJson[str(guild.id)]["ticket"]["panels"]
                for panelID, panelData in panels.items():
                    view = PanelView(panelID, panelData)
                    self.bot.add_view(view)
            logger.info("Views de ticket.py cargados correctamente")
        except Exception as e:
            logger.error(f"Error inesperado al cargar views: {e}")
    
    @commands.hybrid_command(name="createticket", description="Crear un panel para tickets.")
    @IsSU()
    async def createticket(self, ctx, id, title, description, category, name = "ticket"):
        """Crear un nuevo panel de ticket

        Args:
            ctx (ctx): Mensaje
            id (str): Identificador del panel, funciones especiales dependiendo del ID
            title (str): Titulo principal del panel
            description (str): Descripción del panel
            category (str): Categoría donde se desplegarán los nuevos tickets
            name (str, optional): Nombre del ticket nuevo que se crea
        """
        # Prevenir la ejecución de comandos si no esta configurado el bot.
        if CheckSetUp(ctx):
            await ctx.send("Por favor use el comando /setup o hs$setup, antes de ejecutar ningún comando.", reference=ctx.message)
            return

        try :
            message = await ctx.send(embed=SimpleEmbed("Ticket", "Creando panel de ticket", Color.red()))
            panels = configJson[str(ctx.guild.id)]["ticket"]["panels"]
            if not id in panels:
                panels[id] = {
                    "count": 0,
                    "title": title,
                    "description": description,
                    "category": int(category),
                    "name": name
                }
                configJson[str(ctx.guild.id)]["ticket"]["panels"] = panels
                with open("botconfig.json", "w", encoding="utf-8") as file:
                    logger.debug("Escribiendo nueva configuración")
                    dump(configJson, file, indent=4)
                logger.warning("Recargando el fichero de configuración")
                ChargeConfig()
        
            embed = SimpleEmbed(title, description, Color.dark_blue())
            await message.edit(embed=embed, view=PanelView(id, panels[id]))
        except Exception as e:
            logger.error(f"Error inesperado en crear el ticket {id}: {e}")
            
    @createticket.error
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
            logger.error(f"Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando")
            embed = SimpleEmbed("Permiso Denegado", "No tienes permisos para ejecutar este comando.", Color.red())
            await ctx.send(embed=embed, reference=ctx.message)

# Auto run
async def setup(bot):
    await bot.add_cog(Ticket(bot))
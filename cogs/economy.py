from discord import Color, Embed
from discord.ext import commands

from func.logger import get_logger
from func.database import DatabaseConnect
from templates.embeds import SimpleEmbed

logger = get_logger(__name__)

class Economy(commands.Cog):
    """Contiene comandos sobre economía del bot

    Args:
        commands (Cog): Necesario para el funcionamiento de los cogs
    """
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="profile", description="Perfil del usuario en el servidor.")
    async def profile(self, ctx):
        """Muestra el perfil del usuario dentro del servidor

        Args:
            ctx (ctx): Mensaje
        """
        try:
            conn = DatabaseConnect(ctx.guild.id)
            cursor = conn.cursor()
            cursor.execute("SELECT money FROM economy WHERE id = ?", (str(ctx.author.id),))
            data = cursor.fetchone()
            embed = SimpleEmbed(f"Perfil de {ctx.author.name}", f"Dinero: {data[0]}$", Color.yellow())
            embed.set_thumbnail(url=f"{ctx.author.avatar.url}")
            await ctx.send(embed=embed, reference=ctx.message)
        except Exception as e:
            logger.error(f"Error inesperado {e}")
    
    # TODO: Implementar bien la economía en el bot
    
    @commands.hybrid_command(name="daily", description="Recompensa diaria")
    async def daily(self, ctx):
        """Recompensa diaria después de completar misiones
        
        Args:
            ctx (ctx): Mensaje
        """
        # TODO: Terminar de dar la recompensa diaria
        conn = DatabaseConnect(ctx.guild.id)
        cursor = conn.cursor()
        
        cursor.execute(f"""SELECT money FROM economy WHERE id = {ctx.author.id}""")
        
    # TODO: Crear una tienda de puntos para gasta las monedas
    # TODO: Pensar en diferentes recompensas que poder reclamar
        
# Auto run
async def setup(bot):
    await bot.add_cog(Economy(bot))
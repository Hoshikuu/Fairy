#                                                                    ---------------------------------
#
#                                                                       Script  creado por  Hoshiku
#                                                                       https://github.com/Hoshikuu
#
#                                                                    ---------------------------------

# settings.py - V2.0

import discord
from discord.ext import commands

from secrets import token_urlsafe

from func.logger import get_logger
from func.database import insert_global_db, select_global_db, update_global_db
from models.embeds import SimpleEmbed

logger = get_logger(__name__)

class Settings(commands.Cog):
    """Comandos relacionados con la configuración del bot

    Args:
        commands (Cog): Cog
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.hybrid_command(name="token", description="Muestra el token y la contraseña para la configuración web.")
    # TODO: SOLO PERMISOS DE ADMINISTRADOR
    #@IsSU()
    async def token(self, ctx: commands.context.Context):
        """Genera un nuevo token y contraseña para la configuración web y los muestra en un embed

        Args:
            ctx (commands.context.Context): mensaje
        """
        try:
            db_info = select_global_db(str(ctx.guild.id))
            token = token_urlsafe(16)
            password = token_urlsafe(8)
            
            if db_info is None:
                if not insert_global_db(str(ctx.guild.id), token, password):
                    logger.critical(f"Error al insertar el token y la contraseña en la base de datos global para el servidor {ctx.guild.id}")
                    embed = SimpleEmbed("Error", "Ha ocurrido un error al generar el token y la contraseña. Por favor, inténtalo de nuevo más tarde.", discord.Color.red())
                    await ctx.send(embed=embed, reference=ctx.message)
                    return
                logger.info(f"Insertando nuevo servidor {ctx.guild.id} a la base de datos global")
            else:
                if not update_global_db(str(ctx.guild.id), token, password):
                    logger.critical(f"Error al actualizar el token y la contraseña en la base de datos global para el servidor {ctx.guild.id}")
                    embed = SimpleEmbed("Error", "Ha ocurrido un error al generar el token y la contraseña. Por favor, inténtalo de nuevo más tarde.", discord.Color.red())
                    await ctx.send(embed=embed, reference=ctx.message)
                    return
                logger.info(f"Actualizando token y contraseña del servidor {ctx.guild.id} en la base de datos global")
                
            embed = SimpleEmbed("Token de configuración web", f"Token: `{token}`\nContraseña: `{password}`\n\nUsa estos datos para iniciar sesión en la [interfaz web](https://fairy.hoshiku.dev).", discord.Color.blue())
            await ctx.send(embed=embed, reference=ctx.message)
            logger.info(f"{ctx.author.id} ha generado un nuevo token y contraseña para la configuración web")
        except Exception as e:
            logger.critical(f"Si solo ves este mensaje de error, este error es muy inesperado en el script: {e}")
            return
        
    @token.error
    async def permission_error(self, ctx: commands.context.Context, error):
        if isinstance(error, commands.MissingAnyRole):
            logger.error(f"Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando")
            embed = SimpleEmbed("Permiso Denegado", "No tienes permisos para ejecutar este comando.", discord.Color.red())
            await ctx.send(embed=embed, reference=ctx.message)

async def setup(bot: commands.Bot):
    await bot.add_cog(Settings(bot))
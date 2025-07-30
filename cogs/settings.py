# Modulos de discord
from discord import Color
from discord.ext import commands

# Modulo de funciones
from func.botconfig import configJson, IsSU, DefaultServerConfig
from func.terminal import printr

from templates.views import SetupView
from templates.embeds import SimpleEmbed

# Para comandos que esten relacionados a la configuracion del bot
class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="setup", description="Inicia la configuración interactiva del bot.")
    @IsSU()
    async def setup(self, ctx):
        if str(ctx.guild.id) not in configJson:
            printr(f"El servidor {ctx.guild.id} no tiene un json de configuración.", 2)
            DefaultServerConfig(ctx.guild.id)

        view = SetupView(authorID=ctx.author.id, guildID=ctx.guild.id)
        msg = await ctx.send(embed=view.embed, view=view, ephemeral=False)
        view.message = msg
        
    # Esto indica si la funcion da error ejecutar esto
    @setup.error
    # Error de permisos, Falta de permisos
    async def permission_error(self, ctx, error):
        if isinstance(error, commands.MissingAnyRole): # Comprobar que falta un rol
            printr(f"Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando.", 3)
            embed = SimpleEmbed("Permiso Denegado", "No tienes permisos para ejecutar este comando.", Color.red())
            await ctx.send(embed=embed, reference=ctx.message)

# Autorun
async def setup(bot):
    await bot.add_cog(Settings(bot))
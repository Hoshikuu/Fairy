# Modulos de discord
import discord
from discord.ext import commands

# Modulo para el JSON
from json import dump

# Modulo de funciones
from func.botconfig import configJson, CheckSetUp, ChargeConfig
from func.terminal import printr

# Para comandos que esten relacionados a la configuracion del bot
class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Ejecutar el comando para poder usar otros comandos
    # Pide de argumentos la configuracion basica
    @commands.bot.hybrid_command(name="setup", description="Hace la configuracion inicial del bot.")
    async def setup(self, ctx: commands.Context, prefix: str, staff: str):
        guildID = str(ctx.guild.id)
        configJson[guildID]["setup"] = 1
        configJson[guildID]["prefix"] = prefix
        configJson[guildID]["su"] = [staff]

        # Guardar la nueva configuracion
        with open("botconfig.json", "w") as file:
            dump(configJson, file, indent=4)
        
        printr(f"Setup del bot completado en el servidor {guildID}.", 1)
        ChargeConfig() # Recarga la configuracion del bot

        await ctx.send("Setup del bot completado.", reference=ctx.message)

    # Funcion para cambiar el prefijo en la configuracion del bot
    # La funcion pide un argumento, el prefijo nuevo
    @commands.hybrid_command(name="setprefix", description="Establece el prefijo del bot.")
    @commands.has_any_role("Miembro")
    async def setprefix(self, ctx, prefix):
        # Prevenir la ejecucion de comandos si no esta configurado el bot.
        if CheckSetUp(ctx):
            await ctx.send("Porfavor use el comando /setup o hs$setup, antes de ejecutar ningun comando.", reference=ctx.message)
            return
        
        configJson[str(ctx.guild.id)]["prefix"] = prefix # El nuevo prefijo
        with open("botconfig.json", "w") as file:
            dump(configJson, file, indent=4)
        
        printr(f"Prefijo del servidor {ctx.guild.id} cambiado a {prefix}.", 1)
        ChargeConfig() # Recarga la configuracion del bot
        
        await ctx.send(f"Prefijo cambiado a: `{prefix}`", reference=ctx.message)

    @setprefix.error
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
    await bot.add_cog(Settings(bot))
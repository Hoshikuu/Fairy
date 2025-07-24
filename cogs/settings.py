import discord
from discord.ext import commands
from json import dump

from func.botconfig import configJson, CheckSetUp, ChargeConfig
from func.terminal import now

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Setup del bot
    # Para la configuracion incial del bot al servidor
    #! El bot no va a ejecutar ningun comando hasta que no se ejecute el setup
    @commands.bot.hybrid_command(name="setup", description="Hace la configuracion inicial del bot.")
    async def setup(self, ctx: commands.Context, prefix: str, staff: str):
        guildID = str(ctx.guild.id)
        configJson[guildID]["setup"] = 1
        configJson[guildID]["prefix"] = prefix
        configJson[guildID]["su"] = [staff]
        with open("botconfig.json", "w") as file:
            dump(configJson, file, indent=4)
        print(f"{now()} INFO     Setup del bot completado en el servidor {guildID}.")
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
            
        ChargeConfig() # Recarga la configuracion del bot
        print(f"{now()} INFO     Fichero de configuracion recargado.")
        
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
            print(f"{now()} EXEP     Error de permiso, {ctx.author} no tiene los permisos requeridos para ejecutar este comando.")
            await ctx.send(embed=embed, reference=ctx.message)

async def setup(bot):
    await bot.add_cog(Settings(bot))
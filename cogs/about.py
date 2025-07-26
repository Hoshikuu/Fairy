# Modulos de discord
import discord
from discord.ext import commands

# Modulos de funciones
from func.botconfig import CheckSetUp
from func.version import __tag__, __commit__, __branch__

# Comandos que muestran cosas sobre el bot
class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Informacion basica del bot
    #* Esto hay que tenerlo en cuenta, Este comando Hybrido funciona si usaras comandos de prefijo pero tambien te los añade en el command tree asi que son utiles para no repetir mucho codigo
    @commands.hybrid_command(name="info", description="Muestra la información básica del bot")
    async def info(self, ctx: commands.Context):
        embed = discord.Embed(
            title="HoyoStars",
            description="Un bot privado para el servidor HoyoStars.",
            color=discord.Color.blue()
        )

        # Para obtener el usuario correctamente en ambos casos
        user = ctx.author if ctx.author else ctx.user
        embed.set_author(name=user.name, icon_url=user.avatar.url)

        embed.add_field(name="Ping", value=f"{round(ctx.bot.latency * 1000)}ms", inline=False)
        embed.add_field(name="Creador", value="yhoshiku", inline=True)
        embed.set_footer(text="Gracias por usarme ❤️")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="version", description="Muestra la información básica del bot")
    async def version(self, ctx: commands.Context):
        embed = discord.Embed(
            title="HoyoStars",
            description=f"Actualmente estoy en la version {__tag__}",
            color=discord.Color.green()
        )

        embed.add_field(name="Branch", value=__branch__, inline=False)
        embed.add_field(name="Commit", value=__commit__, inline=True)
        embed.set_footer(text="A futuro mas y mejor.")

        await ctx.send(embed=embed)

# Autorun
async def setup(bot):
    await bot.add_cog(About(bot))
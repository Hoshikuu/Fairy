# Modulos de discord
from discord import Color
from discord.ext import commands

# Modulos del bot
from func.version import __tag__, __commit__, __branch__
from templates.embeds import SimpleEmbed

# About Commands
class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Información básica del bot
    @commands.hybrid_command(name="info", description="Muestra la información básica del bot")
    async def info(self, ctx):
        embed = SimpleEmbed("HoyoStars", "Un bot privado para el servidor HoyoStars.", Color.dark_blue())
        embed.add_field(name="Ping", value=f"{round(ctx.bot.latency * 1000)}ms", inline=False)
        embed.add_field(name="Creador", value="<@853193606529024041>", inline=True)
        embed.set_footer(text="Subanme el sueldo.")
        await ctx.send(embed=embed)

    # Muestra la versión actual del bot
    @commands.hybrid_command(name="version", description="Muestra la versión actual del bot")
    async def version(self, ctx):
        embed = SimpleEmbed("HoyoStars", f"Actualmente estoy en la versión {__tag__} !", Color.magenta())
        embed.add_field(name="GitHub", value="https://github.com/Hoshikuu/HoyoStars", inline=True)
        embed.set_footer(text="A futuro más y mejor.")
        await ctx.send(embed=embed)

# Autorun
async def setup(bot):
    await bot.add_cog(About(bot))
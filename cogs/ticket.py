# Modulo de discord
import discord
from discord.ext import commands

from templates.views import PanelView

# Template for cog
class Template(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="createticket", description="Crear un panel para tickets.")
    async def createticket(self, ctx, title, description, category, name):
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.green()
        )

        await ctx.send(embed=embed, view=PanelView(ctx, category, name))

# Autorun
async def setup(bot):
    await bot.add_cog(Template(bot))
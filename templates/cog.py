# Modulo de discord
import discord
from discord.ext import commands

# Template for cog
class Template(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Commands goes here

# Autorun
async def setup(bot):
    await bot.add_cog(Template(bot))
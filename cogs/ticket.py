# Modulo de discord
import discord
from discord.ext import commands

from templates.views import PanelView

from json import dump

from func.terminal import printr
from func.botconfig import configJson, ChargeConfig, CheckSetUp

# Template for cog
class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            panels = configJson[str(guild.id)]["ticket"]["panels"]
            for panel_id, panel_data in panels.items():
                view = PanelView(panel_id, panel_data)
                self.bot.add_view(view)
        printr(f"Views de ticket.py cargados correctamente.", 1)
    
    @commands.hybrid_command(name="createticket", description="Crear un panel para tickets.")
    async def createticket(self, ctx, id, title, description, category, name):
        # Prevenir la ejecucion de comandos si no esta configurado el bot.
        if CheckSetUp(ctx):
            await ctx.send("Porfavor use el comando /setup o hs$setup, antes de ejecutar ningun comando.", reference=ctx.message)
            return

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.green()
        )
        panels = configJson[str(ctx.guild.id)]["ticket"]["panels"]
        if not id in panels:
            panels[id] = {
                "title": title,
                "description": description,
                "category": int(category),
                "name": name
            }
            configJson[str(ctx.guild.id)]["ticket"]["panels"] = panels
            with open("botconfig.json", "w", encoding="utf-8") as file:
                dump(configJson, file, indent=4)
            ChargeConfig()
       
        await ctx.send(embed=embed, view=PanelView(id, panels[id]))

# Autorun
async def setup(bot):
    await bot.add_cog(Ticket(bot))
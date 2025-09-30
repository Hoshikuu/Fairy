import discord

from json import dump

from func.botconfig import ChargeConfig, configJson

from models.modals import *
from models.embeds import SimpleEmbed

class NextButton(discord.ui.Button):
    def __init__(self, parentView):
        super().__init__(label="Siguiente", style=discord.ButtonStyle.primary)
        self.parentView = parentView

    async def callback(self, interaction: discord.Interaction):
        self.parentView.page += 1
        await self.parentView.UpdateEmbed()
        await interaction.response.defer()

class PrevButton(discord.ui.Button):
    def __init__(self, parentView):
        super().__init__(label="Anterior", style=discord.ButtonStyle.secondary)
        self.parentView = parentView

    async def callback(self, interaction: discord.Interaction):
        self.parentView.page -= 1
        await self.parentView.UpdateEmbed()
        await interaction.response.defer()

class PrefixButton(discord.ui.Button):
    def __init__(self, parentView):
        super().__init__(label="Editar Prefix", style=discord.ButtonStyle.green)
        self.parentView = parentView

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PrefixModal(self.parentView))

class SuButton(discord.ui.Button):
    def __init__(self, parentView):
        super().__init__(label="Editar Staff", style=discord.ButtonStyle.green)
        self.parentView = parentView

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SuModal(self.parentView))

class TicketWelcButton(discord.ui.Button):
    def __init__(self, parentView):
        super().__init__(label="Editar Bienvenida", style=discord.ButtonStyle.green)
        self.parentView = parentView

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketWelcModal(self.parentView))

class TicketButton(discord.ui.Button):
    def __init__(self, parentView):
        super().__init__(label="Editar Ticket", style=discord.ButtonStyle.green)
        self.parentView = parentView

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.parentView))

class TicketSuButton(discord.ui.Button):
    def __init__(self, parentView):
        super().__init__(label="Editar Staff Ticket", style=discord.ButtonStyle.green)
        self.parentView = parentView

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketSuModal(self.parentView))

class LogButton(discord.ui.Button):
    def __init__(self, parentView):
        super().__init__(label="Editar Log", style=discord.ButtonStyle.green)
        self.parentView = parentView
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(LogModal(self.parentView))

class SaveButton(discord.ui.Button):
    def __init__(self, parentView):
        super().__init__(label="Guardar Configuración", style=discord.ButtonStyle.success)
        self.parentView = parentView

    async def callback(self, interaction: discord.Interaction):
        guildID = self.parentView.guildID

        config = configJson[guildID]

        config["setup"] = 1
        config["prefix"] = self.parentView.prefix or "hs$"
        config["su"] = [int(i.strip()) for i in self.parentView.su.split(",")]
        config["ticket"]["general"] = int(self.parentView.Tgeneral)
        config["ticket"]["mensaje"] = self.parentView.Tmensaje
        config["ticket"]["category"] = int(self.parentView.Tcategory)
        config["ticket"]["miembro"] = int(self.parentView.Tmiembro)
        config["ticket"]["su"] = [int(i.strip()) for i in self.parentView.Tsu.split(",")]

        configJson[guildID] = config

        with open("botconfig.json", "w", encoding="utf-8") as f:
            dump(configJson, f, indent=4)
        ChargeConfig()
        
        embed=SimpleEmbed("Configuración Guardada", "La configuración del Setup fue guardada correctamente, vuelve a ejecutar el comando si deseas cambiar algo.", discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=None)
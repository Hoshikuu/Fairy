import discord

class PrefixModal(discord.ui.Modal, title="Configurar prefix"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.prefixInput = discord.ui.TextInput(
            label="Prefix del bot",
            placeholder="Ejemplo: hs$",
            default=self.view.prefix or "hs$"
        )
        self.add_item(self.prefixInput)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.prefix = self.prefixInput.value.strip()
        await self.view.UpdateEmbed()
        await interaction.response.edit_message(embed=self.view.embed, view=self.view)

class SuModal(discord.ui.Modal, title="Configurar Staff"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.suInput = discord.ui.TextInput(
            label="Roles Staff",
            placeholder="ID Rol (Separado con comas si son mulitples)",
            default=self.view.su or "",
            required=True
        )
        self.add_item(self.suInput)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.su = self.suInput.value.strip()
        await self.view.UpdateEmbed()
        await interaction.response.edit_message(embed=self.view.embed, view=self.view)

class TicketWelcModal(discord.ui.Modal, title="Configurar Bienvenida"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.TgeneralInput = discord.ui.TextInput(
            label="Canal General",
            placeholder="ID de Canal",
            default=self.view.Tgeneral or "",
            required=True
        )
        self.TmensajeInput = discord.ui.TextInput(
            label="Mensaje de Bienvenida",
            placeholder="Texto de bienvenida (<#ID> para mencionar un canal)",
            default=self.view.Tmensaje or "",
            required=True
        )
        self.add_item(self.TgeneralInput)
        self.add_item(self.TmensajeInput)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.Tgeneral = self.TgeneralInput.value.strip()
        self.view.Tmensaje = self.TmensajeInput.value.strip()
        await self.view.UpdateEmbed()
        await interaction.response.edit_message(embed=self.view.embed, view=self.view)

class TicketModal(discord.ui.Modal, title="Configurar Ticket"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.TmiembroInput = discord.ui.TextInput(
            label="Rol de Miembro",
            placeholder="ID de Rol",
            default=self.view.Tmiembro or "",
            required=True
        )
        self.TcategoryInput = discord.ui.TextInput(
            label="Categoria de Tickets",
            placeholder="ID de Categoria",
            default=self.view.Tcategory or "",
            required=True
        )
        self.add_item(self.TmiembroInput)
        self.add_item(self.TcategoryInput)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.Tcategory = self.TcategoryInput.value.strip()
        self.view.Tmiembro = self.TmiembroInput.value.strip()
        await self.view.UpdateEmbed()
        await interaction.response.edit_message(embed=self.view.embed, view=self.view)

class TicketSuModal(discord.ui.Modal, title="Configurar Staff para Ticket"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.TsuInput = discord.ui.TextInput(
            label="Roles Staff",
            placeholder="ID Rol (Separado con comas si son mulitples)",
            default=self.view.Tsu or "",
            required=True
        )
        self.add_item(self.TsuInput)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.Tsu = self.TsuInput.value.strip()
        await self.view.UpdateEmbed()
        await interaction.response.edit_message(embed=self.view.embed, view=self.view)
        
class LogModal(discord.ui.Modal, title="Configurar Canal para Log"):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.logInput = discord.ui.TextInput(
            label="Canal",
            placeholder="ID Canal",
            default=self.view.log or "",
            required=True
        )
        self.add_item(self.logInput)

    async def on_submit(self, interaction: discord.Interaction):
        self.view.log = self.logInput.value.strip()
        await self.view.UpdateEmbed()
        await interaction.response.edit_message(embed=self.view.embed, view=self.view)
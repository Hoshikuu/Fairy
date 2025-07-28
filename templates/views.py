import discord

class PanelView(discord.ui.View):
    def __init__(self, ctx, category, name):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.category = category
        self.name = name

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.primary, custom_id="OpenTicket")
    async def OpenTicket(self, interaction: discord.Interaction, button: discord.ui.Button):
        cat = discord.utils.get(self.ctx.guild.categories, id=int(self.category))
        overwrites = {
            self.ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        canal = await self.ctx.guild.create_text_channel(
            name=f"{self.name}-00000",
            category=cat,
            overwrites=overwrites,
            topic=self.ctx.author.id
        )
        await interaction.response.send_message("Se ha abierto un nuevo ticket.", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verificación", style=discord.ButtonStyle.danger, custom_id="verification")
    async def VerificationButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Verificación",
            description="Porfavor envia una captura de la conversación de tiktok donde se muestre el enlace de invitación con el personaje que deseas ocupar.",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="Consulta", style=discord.ButtonStyle.primary, custom_id="consultation")
    async def ConsultationButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, name="Staff")
        if staff_role:
            await interaction.response.send_message("El staff se pondra en contacto en breves momentos, porfavor, espere.")
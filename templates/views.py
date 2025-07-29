import discord

from func.botconfig import configJson

class PanelView(discord.ui.View):
    def __init__(self, id, data):
        super().__init__(timeout=None)
        self.id = id
        self.data = data

        # Solo un botón para ese panel
        button = discord.ui.Button(
            label=f"Abrir Ticket",
            style=discord.ButtonStyle.primary,
            custom_id=f"openticket_{id}"
        )
        button.callback = self.ButtonCallBack
        self.add_item(button)

    async def ButtonCallBack(self, interaction: discord.Interaction):
        panel = self.data
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=int(panel["category"]))
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(
            name=f'{panel["name"]}-0000',
            category=category,
            overwrites=overwrites,
            topic=str(interaction.user.id)
        )
        await interaction.response.send_message(f"Se ha abierto un nuevo ticket: {channel.mention}", ephemeral=True)

class VeriConfiView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Verificar", style=discord.ButtonStyle.success, custom_id="verification")
    async def Verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticketConfig = configJson[str(interaction.guild_id)]["ticket"]
        if not any((role.name in ticketConfig["su"] for role in interaction.user.roles) or (role.id in ticketConfig["su"] for role in interaction.user.roles)):
            await interaction.response.send_message("Solo un miembro del staff puede usar ese botón.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Verificación",
            description=f"Usuario <@{interaction.channel.topic}> verificado por <@{interaction.user.id}>",
            color=discord.Color.purple()
        )
        
        member = interaction.guild.get_member(int(interaction.channel.topic.strip()))
        rol = interaction.guild.get_role(ticketConfig["miembro"])
        channel = interaction.guild.get_channel(ticketConfig["general"])
        
        if button.disabled == False:
            await member.add_roles(rol)
            await channel.send(f"<@{interaction.channel.topic}> {ticketConfig["mensaje"]}")
            await interaction.response.send_message(embed=embed)
        button.disabled = True
        await interaction.message.edit(view=self)

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Empezar Verificación", style=discord.ButtonStyle.green, custom_id="startverification")
    async def StartVerificationButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Verificación",
            description="Porfavor envia una captura de la conversación de tiktok donde se muestre el enlace de invitación con el personaje que deseas ocupar.",
            color=discord.Color.purple()
        )
        embed.set_footer(text="Grácias por la espera, un staff pasará en breve después de que envies la información solicitada.")
        if button.disabled == False:
            await interaction.response.send_message(embed=embed, view=VeriConfiView())
        button.disabled = True
        await interaction.message.edit(view=self)
        
    @discord.ui.button(label="Cerrar", style=discord.ButtonStyle.danger, custom_id="closeticketverification")
    async def CloseButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        privilegeRoles = configJson[str(interaction.guild_id)]["ticket"]["su"]
        if not any((role.name in privilegeRoles for role in interaction.user.roles) or (role.id in privilegeRoles for role in interaction.user.roles)):
            await interaction.response.send_message("No tienes permisos para usar ese botón.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Cerrar",
            description="Esto deberia cerrar el ticket pero me da palo hacerlo ahora",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed)
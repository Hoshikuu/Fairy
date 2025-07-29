import discord

from func.botconfig import configJson, ChargeConfig

from json import dump

import asyncio

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
            name=f'{panel["name"]}-{panel["count"]:03d}',
            category=category,
            overwrites=overwrites,
            topic=str(interaction.user.id)
        )
        panel["count"] += 1
        configJson[str(guild.id)]["ticket"]["panels"][self.id] = panel
        with open("botconfig.json", "w", encoding="utf-8") as file:
            dump(configJson, file, indent=4)
        ChargeConfig

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

class ClosedTicketToolView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Abrir", style=discord.ButtonStyle.green, custom_id="reopentiket")
    async def ReOpenTicketButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        privilegeRoles = configJson[str(interaction.guild_id)]["ticket"]["su"]
        if not any((role.name in privilegeRoles for role in interaction.user.roles) or (role.id in privilegeRoles for role in interaction.user.roles)):
            await interaction.response.send_message("No tienes permisos para usar ese botón.", ephemeral=True)
            return
        
        # Quitar los permisos a Usuarios
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }
        for roleID in privilegeRoles: # Añadir los roles con permisos
            role = interaction.guild.get_role(roleID)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        overwrites[interaction.guild.get_member(int(interaction.channel.topic))] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        await interaction.channel.edit(overwrites=overwrites, name=f"{interaction.channel.name.replace("closed-", "")}")

        embed = discord.Embed(
            title="Ticket Abierto",
            color=discord.Color.green()
        )

        if button.disabled == False:
           await interaction.response.send_message(f"<@{interaction.channel.topic}>", embed=embed,)
        button.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Borrar", style=discord.ButtonStyle.danger, custom_id="deleteticket")
    async def DeleteTicketButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        privilegeRoles = configJson[str(interaction.guild_id)]["ticket"]["su"]
        if not any((role.name in privilegeRoles for role in interaction.user.roles) or (role.id in privilegeRoles for role in interaction.user.roles)):
            await interaction.response.send_message("No tienes permisos para usar ese botón.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Borrar Ticket",
            description="Este ticket será borrado en 3 segundos.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

        await asyncio.sleep(3)
        await interaction.channel.delete(reason="Ticket cerrado por el staff.")

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
        
        # Quitar los permisos a Usuarios
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False)
        }
        for roleID in privilegeRoles: # Añadir los roles con permisos
            role = interaction.guild.get_role(roleID)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        await interaction.channel.edit(overwrites=overwrites, name=f"closed-{interaction.channel.name}") # Guardar cambios

        embed = discord.Embed(
            title="Ticket Cerrado",
            description="Este ticket esta cerrado, puede volver a abrir el ticket pulsando el botón.",
            color=discord.Color.purple()
        )

        if button.disabled == False:
            await interaction.response.send_message(embed=embed, view=ClosedTicketToolView())
        button.disabled = True
        await interaction.message.edit(view=self)

class SetupView(discord.ui.View):
    def __init__(self, author_id, original_embed: discord.Embed):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.prefix = None
        self.su_roles = []
        self.message: discord.Message = None  # se establecerá al enviarlo
        self.embed = original_embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def update_embed(self):
        # Actualizar el contenido del embed
        self.embed.clear_fields()
        self.embed.add_field(name="Prefix", value=self.prefix or "❌ No configurado", inline=False)
        self.embed.add_field(
            name="Roles SU",
            value=", ".join(map(str, self.su_roles)) if self.su_roles else "❌ No configurado",
            inline=False
        )
        # Editar el mensaje original
        await self.message.edit(embed=self.embed, view=self)

    @discord.ui.button(label="Establecer prefix", style=discord.ButtonStyle.primary)
    async def set_prefix(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✏️ Escribe el prefix que quieres usar:", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            msg = await interaction.client.wait_for("message", timeout=60, check=check)
            self.prefix = msg.content.strip()
            await msg.delete()
            await interaction.followup.send(f"✅ Prefix establecido: `{self.prefix}`", ephemeral=True)
            await self.update_embed()
        except asyncio.TimeoutError:
            await interaction.followup.send("⏱️ Tiempo agotado. Intenta de nuevo.", ephemeral=True)

    @discord.ui.button(label="Establecer roles SU", style=discord.ButtonStyle.primary)
    async def set_su(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📥 Envía los IDs de los roles separados por comas (ej: `123,456`):", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id and m.channel == interaction.channel

        try:
            msg = await interaction.client.wait_for("message", timeout=60, check=check)
            self.su_roles = [int(r.strip()) for r in msg.content.split(",")]
            await msg.delete()
            await interaction.followup.send("✅ Roles SU actualizados correctamente.", ephemeral=True)
            await self.update_embed()
        except asyncio.TimeoutError:
            await interaction.followup.send("⏱️ Tiempo agotado. Intenta de nuevo.", ephemeral=True)
        except ValueError:
            await interaction.followup.send("❌ Asegúrate de usar solo IDs numéricos separados por comas.", ephemeral=True)

    @discord.ui.button(label="Confirmar configuración", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.prefix or not self.su_roles:
            await interaction.response.send_message("⚠️ Asegúrate de haber configurado el prefix y los roles antes de confirmar.", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        configJson[guild_id] = {
            "setup": 1,
            "prefix": self.prefix,
            "su": self.su_roles
        }

        with open("botconfig.json", "w") as file:
            dump(configJson, file, indent=4)

        await interaction.response.send_message("✅ Configuración guardada correctamente.")
        ChargeConfig()
        self.stop()
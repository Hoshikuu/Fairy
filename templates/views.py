import discord

from func.botconfig import configJson, ChargeConfig
from templates.buttons import *

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
        for roleID in configJson[str(guild)]["ticket"]["su"]: # Añadir los roles con permisos
            role = interaction.guild.get_role(roleID)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
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
        if not any(role.id in ticketConfig["su"] for role in interaction.user.roles):
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
        if not any(role.id in privilegeRoles for role in interaction.user.roles):
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
        if not any(role.id in privilegeRoles for role in interaction.user.roles):
            await interaction.response.send_message("No tienes permisos para usar ese botón.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Borrar Ticket",
            description="Este ticket será borrado en 3 segundos.",
            color=discord.Color.red()
        )
        if button.disabled == False:
           await interaction.response.send_message(embed=embed)
        button.disabled = True
        await interaction.message.edit(view=self)

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
        if not any(role.id in privilegeRoles for role in interaction.user.roles):
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
    def __init__(self, authorID, guildID):
        super().__init__(timeout=1200)
        self.authorID = authorID
        self.guildID = str(guildID)
        self.page = 0

        config = configJson[str(guildID)]

        # Datos introducidos
        self.prefix = config["prefix"]
        self.su = None if config["su"] == [] else str(config["su"])[1:-1]
        self.Tgeneral = None if config["ticket"]["general"] == 0 else config["ticket"]["general"] 
        self.Tmensaje = None if config["ticket"]["mensaje"] == "" else config["ticket"]["mensaje"]
        self.Tcategory = None if config["ticket"]["category"] == 0 else config["ticket"]["category"] 
        self.Tmiembro = None if config["ticket"]["miembro"] == 0 else config["ticket"]["miembro"] 
        self.Tsu = None if config["ticket"]["su"] == [] else str(config["ticket"]["su"])[1:-1]
        self.log = None if config["log"] == [] else config["log"]

        self.embed = discord.Embed(color=discord.Color.blurple())
        self.message: discord.Message = None
        self.UpdatePageContent()

    # Funcion para saber si ejecutar los callbacks
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.authorID

    def UpdatePageContent(self):
        self.clear_items()

        match self.page:
            case 0:
                self.embed.title = "Configuración del Bot"
                self.embed.description = (
                    "Bienvenido al asistente de configuración del bot.\n"
                    "Haz clic en \"Siguiente\" para comenzar."
                )
                self.add_item(NextButton(parentView=self))

            case 1:
                self.embed.title = "Configurar Prefix"
                self.embed.description = "Configura el prefix que usará el bot en este servidor."
                self.embed.clear_fields()
                self.embed.add_field(name="Prefix", value=self.prefix or "hs$", inline=False)
                self.add_item(PrevButton(parentView=self))
                self.add_item(PrefixButton(parentView=self))
                self.add_item(NextButton(parentView=self))
            
            case 2:
                self.embed.title = "Configurar Staff"
                self.embed.description = "Configura los roles las cuales formaran parte del staff."
                self.embed.clear_fields()
                self.embed.add_field(name="Roles", value=self.su or "No configurado", inline=False)
                self.add_item(PrevButton(parentView=self))
                self.add_item(SuButton(parentView=self))
                self.add_item(NextButton(parentView=self))

            case 3:
                self.embed.title = "Configurar Tickets Bienvenida"
                self.embed.description = "Configura el canal General y el mensaje de bienvenida que se va a enviar."
                self.embed.clear_fields()
                self.embed.add_field(name="General", value=self.Tgeneral or "No configurado", inline=True)
                self.embed.add_field(name="Mensaje", value=self.Tmensaje or "No configurado", inline=False)
                self.add_item(PrevButton(parentView=self))
                self.add_item(TicketWelcButton(parentView=self))
                self.add_item(NextButton(parentView=self))

            case 4:
                self.embed.title = "Configurar Tickets"
                self.embed.description = "Configura el rol de Miembros y la categoria donde comprobara el contestador automatico."
                self.embed.clear_fields()
                self.embed.add_field(name="Miembro", value=self.Tmiembro or "No configurado", inline=True)
                self.embed.add_field(name="Categoria", value=self.Tcategory or "No configurado", inline=False)
                self.add_item(PrevButton(parentView=self))
                self.add_item(TicketButton(parentView=self))
                self.add_item(NextButton(parentView=self))

            case 5:
                self.embed.title = "Configurar Staff Ticket"
                self.embed.description = "Configura los roles las cuales formaran parte del staff en los tickets."
                self.embed.clear_fields()
                self.embed.add_field(name="Ticket Roles", value=self.Tsu or "No configurado", inline=False)
                self.add_item(PrevButton(parentView=self))
                self.add_item(TicketSuButton(parentView=self))
                self.add_item(NextButton(parentView=self))
                
            case 6:
                self.embed.title = "Configurar Canal Log"
                self.embed.description = "Configura un canal donde el bot mandará los logs."
                self.embed.clear_fields()
                self.embed.add_field(name="Canal Log", value=self.log or "No configurado", inline=False)
                self.add_item(PrevButton(parentView=self))
                self.add_item(TicketSuButton(parentView=self))
                self.add_item(NextButton(parentView=self))
                
            case 7:
                self.embed.title = "Confirmación"
                self.embed.description = "Revisa los datos y confirma para guardar."
                self.embed.clear_fields()
                self.embed.add_field(name="Prefix", value=self.prefix or "No configurado", inline=True)
                self.embed.add_field(name="Roles", value=self.su or "No configurado", inline=True)
                self.embed.add_field(name="General", value=self.Tgeneral or "No configurado", inline=True)
                self.embed.add_field(name="Mensaje", value=self.Tmensaje or "No configurado", inline=True)
                self.embed.add_field(name="Miembro", value=self.Tmiembro or "No configurado", inline=True)
                self.embed.add_field(name="Categoria", value=self.Tcategory or "No configurado", inline=True)
                self.embed.add_field(name="Ticket Roles", value=self.Tsu or "No configurado", inline=True)
                self.embed.add_field(name="Canal Log", value=self.log or "No configurado", inline=False)
                self.add_item(PrevButton(parentView=self))
                self.add_item(SaveButton(parentView=self))

    async def UpdateEmbed(self):
        self.UpdatePageContent()
        if self.message:
            await self.message.edit(embed=self.embed, view=self)
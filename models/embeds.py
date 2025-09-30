from discord import Embed

def SimpleEmbed(newTitle, newDescription, color):
    """Crea un embed simple

    Args:
        newTitle (str): Titulo del embed
        newDescription (str): Descripción del embed
        color (discord.Color): Color del embed

    Returns:
        discord.Embed: Embed resultante
    """
    embed = Embed(
        title=newTitle,
        description=newDescription,
        color=color
    )
    return embed
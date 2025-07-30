from discord import Embed, Color


def SimpleEmbed(newTitle, newDescription, color):
    embed = Embed(
        title=newTitle,
        description=newDescription,
        color=color
    )
    return embed
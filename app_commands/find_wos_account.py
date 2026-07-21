from discord import Interaction, Member, User
from discordHandler import DiscordClient
from commands.find_account import find_account

async def find_wos_account(client: DiscordClient, interaction: Interaction, user: User):
    if not isinstance(user, Member):
        await interaction.response.send_message('Unable to detect the Discord Member to look up', ephemeral=True)
        return
    await find_account(client, interaction, user, None, None, None)

async def find_wos_account_public(client: DiscordClient, interaction: Interaction, user: User):
    if not isinstance(user, Member):
        await interaction.response.send_message('Unable to detect the Discord Member to look up', ephemeral=True)
        return
    await find_account(client, interaction, user, None, None, '1')

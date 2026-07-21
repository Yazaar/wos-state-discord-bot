from discord import Interaction, Member
from discordHandler import DiscordClient
from events.alliance_request import tnc_alliance_join_req


async def remote_wos_link(client: DiscordClient, interaction: Interaction, member: Member, alliance_code: str, wos_account_id: str):
    handler = interaction.user

    if not isinstance(handler, Member):
        await interaction.response.send_message('Unable to detect which member triggered the command', ephemeral=True)
        return

    if not handler.guild_permissions.administrator:
        await interaction.response.send_message('You have no permission to trigger this command', ephemeral=True)
        return

    await tnc_alliance_join_req(client, interaction, wos_account_id, alliance_code, member)

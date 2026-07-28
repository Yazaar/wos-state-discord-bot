from discord import Interaction, Member
from discordHandler import DiscordClient
from events.alliance_request import tnc_alliance_join_req
from services import get_services


async def remote_wos_link(client: DiscordClient, interaction: Interaction, member: Member, alliance_code: str, wos_account_id: str, wos_account_name: str):
    handler = interaction.user

    if not isinstance(handler, Member):
        await interaction.response.send_message('Unable to detect which member triggered the command', ephemeral=True)
        return

    if not handler.guild_permissions.administrator:
        await interaction.response.send_message('You have no permission to trigger this command', ephemeral=True)
        return

    await tnc_alliance_join_req(client, interaction, wos_account_id, wos_account_name, alliance_code, member)

async def clear_wos_link(client: DiscordClient, interaction: Interaction, wos_account_id: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message(f'Unable to detect discord server', ephemeral=True)
        return
    
    services = get_services()

    wos_link = await services.database.get_wos_links(wos_id=wos_account_id, guild_id=str(guild.id), status='active', limit=1)
    wos_link = wos_link[0] if len(wos_link) == 1 else None

    if not wos_link:
        await interaction.response.send_message(f'Unable to find a WOS Link for account `{wos_account_id}`', ephemeral=True)
        return

    await services.database.update_wos_link(wos_link=wos_link, status='inactive')
    await interaction.response.send_message(f'WOS Link for account `{wos_account_id}` is now cleared and can be claimed by a new discord user', ephemeral=True)

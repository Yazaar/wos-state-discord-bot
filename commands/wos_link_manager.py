from discord import Embed, Guild, Interaction, Member
from commands.generic_wos_selector import generic_wos_selector
from discordHandler import DiscordClient
from services import get_services

async def remove_allowed(guild: Guild, sender: Member, target: Member):
    if (
            sender.guild_permissions.administrator or
            sender.guild_permissions.manage_roles
        ):
        return True

    return False

async def remove_link_selector(client: DiscordClient, interaction: Interaction, target_param: Member | None):
    await generic_wos_selector(client, interaction, target_param, 'remove_link.account', 'Select account to remove', remove_allowed)

async def remove_link_selection(client: DiscordClient, interaction: Interaction):
    if not interaction.data:
        await interaction.response.send_message('Data missing from interaction', ephemeral=True)
        return None

    values = interaction.data.get('values')
    if not values or len(values) < 1:
        await interaction.response.send_message('Data missing from interaction', ephemeral=True)
        return None

    try: selection = int(values[0])
    except Exception:
        await interaction.response.send_message('Invalid data from interaction', ephemeral=True)
        return None

    services = get_services()
    wos_link = await services.database.get_wos_links(id_=selection, limit=1)
    wos_link = wos_link[0] if len(wos_link) > 0 else None

    if not wos_link:
        await interaction.response.send_message('WOS link not found', ephemeral=True)
        return

    services = get_services()

    await services.database.update_wos_link(wos_link, status='inactive')

    embed = Embed(title='WOS account')
    embed.add_field(name='Name', value=wos_link.wos_name, inline=False)
    embed.add_field(name='State', value='2844', inline=False)

    await interaction.response.send_message('WOS account unlinked', ephemeral=True, embed=embed)

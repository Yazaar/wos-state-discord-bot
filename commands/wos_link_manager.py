from discord import Embed, Guild, Interaction, Member
from commands.generic_wos_selector import generic_wos_selector
from discordHandler import DiscordClient
from services import get_services
from utils.wos_api_utils import get_player

async def refresh_allowed(guild: Guild, sender: Member, target: Member):
    if target.id == sender.id: return True

    if (
            sender.guild_permissions.administrator or
            sender.guild_permissions.manage_roles
        ):
        return True

    return False

async def remove_allowed(guild: Guild, sender: Member, target: Member):
    if (
            sender.guild_permissions.administrator or
            sender.guild_permissions.manage_roles
        ):
        return True

    return False

async def __shared_link_manage(client: DiscordClient, interaction: Interaction, require_account: bool):
    if not interaction.data:
        await interaction.response.send_message('Data missing from interaction', ephemeral=True)
        return None, None

    values = interaction.data.get('values')
    if not values or len(values) < 1:
        await interaction.response.send_message('Data missing from interaction', ephemeral=True)
        return None, None

    try: selection = int(values[0])
    except Exception:
        await interaction.response.send_message('Invalid data from interaction', ephemeral=True)
        return None, None

    services = get_services()
    link = await services.database.get_wos_links(id_=selection, limit=1)
    link = link[0] if len(link) > 0 else None

    if not link:
        await interaction.response.send_message('The selection is invalid', ephemeral=True)
        return None, None

    try: wos_id = int(link.wos_id)
    except Exception:
        await interaction.response.send_message('The WOS id is invalid', ephemeral=True)
        return None, None

    try:
        player_data = await get_player(wos_id)
        if not player_data: raise Exception('Player data not found')
    except Exception:
        if not require_account:
            await interaction.response.send_message('Failed to get WOS player data', ephemeral=True)
            return None, link
        player_data = None

    return player_data, link

async def refresh_link_selector(client: DiscordClient, interaction: Interaction, target_param: Member | None):
    await generic_wos_selector(client, interaction, target_param, 'refresh_link.account', 'Select account to refresh', refresh_allowed)

async def refresh_link_selection(client: DiscordClient, interaction: Interaction):
    wos_player, wos_link = await __shared_link_manage(client, interaction, True)

    if not wos_link or not wos_player: return

    services = get_services()

    await services.database.update_wos_link(wos_link, wos_name=wos_player.name)

    wos_acc_embed = Embed(title='WOS account')
    wos_acc_embed.add_field(name='Name', value=wos_player.name, inline=False)
    wos_acc_embed.add_field(name='Furnace', value=wos_player.stove_lvl, inline=False)
    wos_acc_embed.add_field(name='State', value=wos_player.server, inline=False)
    if wos_player.avatar_img: wos_acc_embed.set_thumbnail(url=wos_player.avatar_img)

    await interaction.response.send_message('WOS account refreshed', embed=wos_acc_embed, ephemeral=True)

async def remove_link_selector(client: DiscordClient, interaction: Interaction, target_param: Member | None):
    await generic_wos_selector(client, interaction, target_param, 'remove_link.account', 'Select account to remove', remove_allowed)

async def remove_link_selection(client: DiscordClient, interaction: Interaction):
    wos_player, wos_link = await __shared_link_manage(client, interaction, False)

    if not wos_link: return

    services = get_services()

    await services.database.update_wos_link(wos_link, status='inactive')

    args = {}

    if wos_player:
        embed = Embed(title='WOS account')
        embed.add_field(name='Name', value=wos_player.name, inline=False)
        embed.add_field(name='Furnace', value=wos_player.stove_lvl, inline=False)
        embed.add_field(name='State', value=wos_player.server, inline=False)
        if wos_player.avatar_img: embed.set_thumbnail(url=wos_player.avatar_img)
        args['embed'] = embed

    await interaction.response.send_message('WOS account unlinked', ephemeral=True, **args)

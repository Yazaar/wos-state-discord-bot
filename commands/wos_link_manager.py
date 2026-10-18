from discord import Embed, Guild, Interaction, Member
from commands.generic_wos_selector import generic_wos_selector
from discordHandler import DiscordClient
from services import get_services
from utils.wos_api_utils import test_wos_account

async def remove_allowed(guild: Guild, sender: Member, target: Member):
    if (
            sender.guild_permissions.administrator or
            sender.guild_permissions.manage_roles or
            sender.id == target.id
        ):
        return True

    return False

async def remove_link_selector(client: DiscordClient, interaction: Interaction, target_param: Member | None):
    await generic_wos_selector(client, interaction, target_param, 'remove_link.account', 'Select account to remove', remove_allowed, allow_softlink=True)

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

    alliance = None
    if wos_link.alliance_id:
        alliance = await services.database.get_alliances(id_=wos_link.alliance_id, limit=1)
        alliance = alliance[0] if len(alliance) == 1 else None

    await services.database.update_wos_link(wos_link, status='inactive')

    embed = Embed(title='WOS account')
    embed.add_field(name='Name', value=wos_link.wos_name, inline=False)
    if alliance and alliance.state:
        embed.add_field(name='State', value=str(alliance.state), inline=False)

    await interaction.response.send_message('WOS account unlinked', ephemeral=True, embed=embed)

async def add_wos_account(client: DiscordClient, interaction: Interaction,
        wos_account_id: str, wos_account_name: str, state_number: str, target_member: Member | None
    ):
    try:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message('Unable to detect discord server of message', ephemeral=True)
            return

        try: wos_account_id_int = int(wos_account_id)
        except Exception:
            await interaction.response.send_message('Invalid WOS account id', ephemeral=True)
            return

        try: state_number_int = int(state_number)
        except Exception:
            await interaction.response.send_message('Invalid WOS account state', ephemeral=True)
            return

        guild_id = str(guild.id)

        sender = interaction.user
        if not isinstance(sender, Member):
            await interaction.response.send_message('Unable to detect sender of message', ephemeral=True)
            return

        if target_member:
            if not sender.guild_permissions.administrator:
                await interaction.response.send_message('You do not have permission to do this action on the user', ephemeral=True)
                return
            member = target_member
        else:
            member = sender

        member_id = str(member.id)

        services = get_services()
        wos_links = await services.database.get_wos_links(
            guild_id=guild_id, discord_id=member_id, status=['active', 'unlinked', 'softlink'], wos_id=wos_account_id
        )

        if len(wos_links) > 0:
            await interaction.response.send_message('WOS account is already linked', ephemeral=True)
            return

        try:
            result = await test_wos_account(wos_account_id_int, state_number_int)
            if not result:
                await interaction.response.send_message(f'WOS account not in state {state_number_int}', ephemeral=True)
                return  
        except Exception:
            await interaction.response.send_message('Unable to verify WOS account', ephemeral=True)
            return

        alliance = await services.database.get_alliances(guild_id=guild_id, code='__softlink__', state=state_number_int, show_softlinks=True, limit=1)
        alliance = alliance[0] if len(alliance) == 1 else None

        if not alliance:
            alliance = await services.database.add_alliance('__softlink__', 'WOS Soft Links', state_number_int, guild_id)

        if not alliance:
            await interaction.response.send_message('Something went wrong with state registration', ephemeral=True)
            return

        await services.database.register_wos_link(guild_id, alliance.id, member_id, wos_account_id, wos_account_name, status='softlink')
        await interaction.response.send_message('WOS account added', ephemeral=True)
    except Exception as e:
        print('Failed to handle add_wos_account:', str(e))

import time
from discord import Guild, Interaction, Member
from discord.ui import Select, View
from models.wos_link import WosLink
from utils.app_utils import sort_by_attr
from utils.discord_utils import auto_close_interaction_callback
from commands.generic_wos_selector import generic_wos_selector
from discordHandler import DiscordClient
from models.alliance import Alliance
from services import get_services

async def self_nickname_allowed(guild: Guild, sender: Member, target: Member):
    if (
            sender.guild_permissions.change_nickname or
            sender.guild_permissions.administrator or
            sender.guild_permissions.manage_nicknames
        ):
        return True
    return False

async def any_nickname_allowed(guild: Guild, sender: Member, target: Member):
    if (
            sender.guild_permissions.administrator or
            sender.guild_permissions.manage_nicknames
        ):
        return True
    return False

async def set_nickname(client: DiscordClient, interaction: Interaction, target_param: Member | None):
    await generic_wos_selector(
        client, interaction, target_param, 'nickname.set_on_member', 'Select primary account',
        any_nickname_allowed if target_param and target_param.id != interaction.user.id else self_nickname_allowed)

async def set_nickname_on_member(client: DiscordClient, interaction: Interaction):
    if not interaction.data:
        await interaction.response.send_message(content='Data missing from request', ephemeral=True)
        return
    if not interaction.guild:
        await interaction.response.send_message(content='Unable to detect which server the interaction originates from', ephemeral=True)
        return
    values = interaction.data.get('values', None)
    if not values or len(values) < 1:
        await interaction.response.send_message(content='Data is empty in request', ephemeral=True)
        return

    try: value_num = int(values[0])
    except Exception:
        await interaction.response.send_message(content='Selection is of invalid type', ephemeral=True)
        return

    services = get_services()
    link = await services.database.get_wos_links(id_=value_num, limit=1)
    if len(link) == 0:
        await interaction.response.send_message(content='Unable to find selection', ephemeral=True)
        return
    link = link[0]

    try: member = await interaction.guild.fetch_member(int(link.discord_id))
    except Exception:
        await interaction.response.send_message(content='Unable to find discord account', ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    role_ids = [str(i.id) for i in member.roles]
    alliance_role_tags = await services.database.get_guild_tags(guild_id=guild_id, value=role_ids, tag='alliance_role_base')
    sort_by_attr(alliance_role_tags, role_ids, 'value')
    alliance_role_tags.reverse()

    if len(alliance_role_tags) == 0:
        await interaction.response.send_message(content='Unable to find member alliances', ephemeral=True)
        return
    alliance_ids = []
    for i in alliance_role_tags:
        if i.space:
            try: space_num = int(i.space)
            except Exception: continue
            alliance_ids.append(space_num)

    alliances = await services.database.get_alliances(id_=alliance_ids)
    sort_by_attr(alliances, alliance_ids, 'id')

    if len(alliances) == 0:
        await interaction.response.send_message(content='Unable to find linked alliances', ephemeral=True)
        return

    if len(alliances) == 1:
        await set_nickname_on_alliance(client, interaction, link, alliances[0])
        return

    view = View()
    select = Select(custom_id=f'nickname.set_on_alliance::{link.id}', max_values=len(alliances))
    select.callback = auto_close_interaction_callback(interaction)
    for i in alliances:
        select.add_option(label=i.name, value=str(i.id))

    view.add_item(select)
    await interaction.response.send_message(content='Select alliance', view=view, ephemeral=True)

async def set_nickname_on_alliance(client: DiscordClient, interaction: Interaction, link_id: str | int | WosLink, alliance: Alliance | None = None):
    if not interaction.guild:
        await interaction.response.send_message(content='Unable to detect which server the interaction originates from', ephemeral=True)
        return

    if isinstance(link_id, str):
        try: link_id = int(link_id)
        except Exception:
            await interaction.response.send_message(content='WOS link id is invalid', ephemeral=True)
            return

    services = get_services()

    if isinstance(link_id, int):
        found_link = await services.database.get_wos_links(id_=link_id, limit=1)
        if len(found_link) == 0:
            await interaction.response.send_message(content='WOS link not found', ephemeral=True)
            return
        link_id = found_link[0]

    if not isinstance(link_id, WosLink):
        await interaction.response.send_message(content='Unable to find WOS link', ephemeral=True)
        return

    alliances = [alliance] if alliance else None

    if not alliances:
        if not interaction.data:
            await interaction.response.send_message(content='Data missing', ephemeral=True)
            return
        alliance_ids = interaction.data.get('values', None)
        if not alliance_ids or len(alliance_ids) < 1:
            await interaction.response.send_message(content='Data value missing', ephemeral=True)
            return
        try: alliance_ids = [int(i) for i in alliance_ids]
        except Exception:
            await interaction.response.send_message(content='Alliance id of invalid type', ephemeral=True)
            return
        alliances = await services.database.get_alliances(id_=alliance_ids, limit=len(alliance_ids))
        if not alliances or len(alliances) == 0:
            await interaction.response.send_message(content='Alliance not found', ephemeral=True)
            return
        sort_by_attr(alliances, alliance_ids, 'id')

    try: member = await interaction.guild.fetch_member(int(link_id.discord_id))
    except Exception:
        await interaction.response.send_message(content='Unable to detect target discord member', ephemeral=True)
        return

    alliance_codes = '/'.join([i.code for i in alliances])

    try: await member.edit(nick=f'[{alliance_codes}] {link_id.wos_name}')
    except Exception as e:
        print('Edit nickname error:', str(e))
        await interaction.response.send_message(content='Failed to edit nickname of discord member', ephemeral=True)
        return

    await interaction.response.send_message(content='Discord member nickname updated', ephemeral=True)

async def set_all_nicknames(client: DiscordClient, interaction: Interaction):
    sent_response = False
    try:
        if not isinstance(interaction.user, Member):
            await interaction.response.send_message('Unable to detect what member triggered the command', ephemeral=True)
            return

        if not interaction.guild:
            await interaction.response.send_message('Unable to detect what server the command originates from', ephemeral=True)
            return

        services = get_services()

        guild_id = str(interaction.guild.id)
        alliance_roles = await services.database.get_guild_tags(guild_id=guild_id, tag='alliance_role_base')
        alliance_ids = []

        for i in alliance_roles:
            if i.space:
                try: space = int(i.space)
                except Exception: continue
                alliance_ids.append(space)

        if len(alliance_ids) == 0:
            await interaction.response.send_message('Unable to find any alliances', ephemeral=True)
            return    

        start_time = int(time.time())
        await interaction.response.send_message(f'Updating member nicknames... (<t:{start_time}:R>)', ephemeral=True)
        sent_response = True

        alliances = await services.database.get_alliances(id_=alliance_ids)

        role_map = {}
        for role in alliance_roles:
            for alliance in alliances:
                if not role.space: continue
                try: space_num = int(role.space)
                except Exception: continue
                if space_num != alliance.id: continue
                try: role_num = int(role.value)
                except Exception: continue
                role_map[role_num] = alliance

        async for member in interaction.guild.fetch_members():
            member_wos_link = await services.database.get_wos_links(guild_id=guild_id, discord_id=str(member.id), limit=1, status='active')
            if len(member_wos_link) == 0: continue
            member_wos_link = member_wos_link[0]

            codes = []
            for role in member.roles:
                member_alliance = role_map.get(role.id, None)
                if not isinstance(member_alliance, Alliance): continue
                codes.append(member_alliance.code)

            codes.reverse()
            prefix = '/'.join(codes)
            if prefix: prefix = f'[{prefix}] '
            try: await member.edit(nick=f'{prefix}{member_wos_link.wos_name}')
            except Exception: pass
            

        total_time = int(time.time()) - start_time
        try: await interaction.edit_original_response(content=f'Member nicknames processed on {total_time}s')
        except Exception as e:
            print('Failed to edit message:', str(e))
    except Exception as e:
        print('Failed to handle nickname_manager.set_all_nicknames:', str(e))
        if sent_response: await interaction.response.edit_message(content='Failed to process command')
        else: await interaction.response.send_message('Failed to process command')

from discord import Interaction, Member, PermissionOverwrite, Permissions, CategoryChannel
from discordHandler import DiscordClient
from services import get_services

async def alliance_create(client: DiscordClient, interaction: Interaction, alliance_code: str, alliance_name: str, state: int):
    try:
        member = interaction.user
        if not isinstance(member, Member):
            await interaction.response.send_message('Unable to recognize the sender of the command', ephemeral=True)
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message('Unable to identify the server for this interaction', ephemeral=True)
            return

        if not state or state < 0:
            await interaction.response.send_message('Invalid state number', ephemeral=True)
            return

        alliance_code_lower = alliance_code.lower()

        services = get_services()
        alliances = await services.database.get_alliances(guild_id=str(guild.id), code=alliance_code, state=state, limit=1)
        if len(alliances) > 0:
            await interaction.response.send_message(f'⚠️ Unable to add *[{alliance_code}] {alliance_name}* since *[{alliance_code}] {alliances[0].name} ({state})* already exists', ephemeral=True)
            return

        join_requests_channel_name = f'{alliance_code_lower}-join-requests'

        guild_id = str(guild.id)

        join_requests_category_info = await services.database.get_guild_tags(tag='join-req.category', guild_id=guild_id, limit=1)
        join_requests_category_info = join_requests_category_info[0] if len(join_requests_category_info) > 0 else None

        if not join_requests_category_info or not join_requests_category_info.value:
            await interaction.response.send_message('Join requests channel category not registered for the server', ephemeral=True)
            return

        try:
            join_requests_category_id = int(join_requests_category_info.value)
        except Exception:
            await interaction.response.send_message('Unable to process the channel category due to being in a broken format, please re-register category', ephemeral=True)
            return

        join_requests_category = guild.get_channel(join_requests_category_id)
        if not isinstance(join_requests_category, CategoryChannel):
            await interaction.response.send_message('Unable to find the join requests channel category, please re-register category', ephemeral=True)
            return

        state_nr_str = str(state)

        state_role = await services.database.get_guild_tags(tag='state.role', guild_id=guild_id, space=state_nr_str, limit=1)
        state_role = state_role[0] if len(state_role) > 0 else None

        if not state_role:
            state_role_instance = await guild.create_role(name=f'State {state_nr_str}', permissions=Permissions(0))
            await services.database.add_guild_tag(guild_id, str(state_role_instance.id), 'state.role', space=state_nr_str)

        base_role = await guild.create_role(name=f'{alliance_code} Member', permissions=Permissions(0))

        join_req_ch = await join_requests_category.create_text_channel(name=join_requests_channel_name)
        await join_req_ch.set_permissions(base_role, overwrite=PermissionOverwrite(view_channel=True))

        alliance = await services.database.add_alliance(alliance_code, alliance_name, state, guild_id)
        await services.database.add_guild_tag(guild_id, str(base_role.id), 'alliance_role_base', space=str(alliance.id))
        await services.database.add_guild_tag(guild_id, str(join_req_ch.id), 'alliance_jrc', space=str(alliance.id))

        await interaction.response.send_message(f'Alliance *[{alliance_code}] {alliance_name}* added!', ephemeral=True)
    except Exception as e:
        print('Failed to handle alliance_create:', str(e))

async def alliance_remove(client: DiscordClient, interaction: Interaction, alliance_id_str: str):
    member = interaction.user
    if not isinstance(member, Member):
        await interaction.response.send_message('Unable to recognize the sender of the command', ephemeral=True)
        return
    
    try: alliance_id = int(alliance_id_str)
    except Exception:
        await interaction.response.send_message('Specified alliance is of invalid type', ephemeral=True)
        return


    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to identify the server for this interaction', ephemeral=True)
        return

    guild_id = str(guild.id)

    services = get_services()

    alliance = await services.database.get_alliances(id_=alliance_id, limit=1)
    alliance = alliance[0] if len(alliance) > 0 else None    

    if alliance:
        join_req_ch = await services.database.get_guild_tags(guild_id=guild_id, tag='alliance_jrc', space=str(alliance.id), limit=1)
        try: join_req_ch_entity = guild.get_channel(int(join_req_ch[0].value))
        except Exception: join_req_ch_entity = None
        if join_req_ch_entity:
            await join_req_ch_entity.delete(reason='Alliance removed') 

        alliance_role_base = await services.database.get_guild_tags(guild_id=guild_id, tag='alliance_role_base', space=str(alliance.id), limit=1)
        try: alliance_role_base_entity = guild.get_role(int(alliance_role_base[0].value))
        except Exception: alliance_role_base_entity = None
        if alliance_role_base_entity:
            await alliance_role_base_entity.delete(reason='Alliance removed')

        await services.database.remove_alliance(alliance)

    alliance_identity = f' *[{alliance.code}] {alliance.name}*' if alliance else ''

    await interaction.response.send_message(f'Alliance{alliance_identity} removed', ephemeral=True)

from discord import Guild, Interaction, Member, PermissionOverwrite, Permissions, CategoryChannel, Role, TextChannel
from discordHandler import DiscordClient
from models.alliance import Alliance
from services import Services, get_services

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

        guild_id = str(guild.id)

        services = get_services()
        alliances = await services.database.get_alliances(guild_id=guild_id, code=alliance_code, state=state, limit=1)
        if len(alliances) > 0:
            await interaction.response.send_message(f'⚠️ Unable to add *[{alliance_code}] {alliance_name}* since *[{alliance_code}] {alliances[0].name} ({state})* already exists', ephemeral=True)
            return

        alliance = await services.database.add_alliance(alliance_code, alliance_name, state, guild_id)

        setup_info = await setup_alliance_on_server(client, interaction, alliance, guild, services)
        if not setup_info[0]:
            return

        await interaction.response.send_message(f'Alliance *[{alliance_code}] {alliance_name}* added!', ephemeral=True)
    except Exception as e:
        print('Failed to handle alliance_create:', str(e))

async def alliance_remove(client: DiscordClient, interaction: Interaction, alliance_id_str: str):
    try:
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
    except Exception as e:
        print('Failed to handle alliance_remove:', str(e))

async def alliance_update(client: DiscordClient, interaction: Interaction, alliance_id_str: str, alliance_code: str, alliance_name: str, state: int):
    try:
        services = get_services()

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message('Unable to identify the server for this interaction', ephemeral=True)
            return
        guild_id = str(guild.id)

        alliance = await services.database.get_alliances(id_=alliance_id_str, limit=1)
        alliance = alliance[0] if len(alliance) == 1 else None
        if not alliance:
            await interaction.response.send_message('Alliance not found', ephemeral=True)
            return

        alliance = await services.database.update_alliance(alliance, alliance_code, alliance_name, state)

        join_req_ch = await services.database.get_guild_tags(guild_id=guild_id, tag='alliance_jrc', space=str(alliance.id), limit=1)
        try: join_req_ch_entity = guild.get_channel(int(join_req_ch[0].value))
        except Exception: join_req_ch_entity = None
        if join_req_ch_entity:
            try: await join_req_ch_entity.edit(name=f'{alliance_code.lower()}-join-requests')
            except Exception: pass

        setup_info = await setup_alliance_on_server(client, interaction, alliance, guild, services)
        if not setup_info[0]:
            return

        await interaction.response.send_message(
            f'Alliance updated to [{alliance.code}] {alliance.name} ({alliance.state})',
            ephemeral=True
        )
    except Exception as e:
        print('Failed to handle alliance_update:', str(e))

async def setup_alliance_on_server(
        client: DiscordClient, interaction: Interaction, alliance: Alliance, guild: Guild, services: Services
    ):
    guild_id = str(guild.id)

    join_requests_category_info = await services.database.get_guild_tags(tag='join-req.category', guild_id=guild_id, limit=1)
    join_requests_category_info = join_requests_category_info[0] if len(join_requests_category_info) > 0 else None

    if not join_requests_category_info or not join_requests_category_info.value:
        await interaction.response.send_message('Join requests channel category not registered for the server, please register category and then complete setup by modifying alliance with all edit fields empty', ephemeral=True)
        return None, None, None, None

    try: join_requests_category_id = int(join_requests_category_info.value)
    except Exception:
        await interaction.response.send_message('Unable to process the channel category due to being in a broken format, please re-register category and then complete setup by modifying alliance with all edit fields empty', ephemeral=True)
        return None, None, None, None

    join_requests_category = guild.get_channel(join_requests_category_id)
    if not isinstance(join_requests_category, CategoryChannel):
        await interaction.response.send_message('Unable to find the join requests channel category, please re-register category and then complete setup by modifying alliance with all edit fields empty', ephemeral=True)
        return None, None, None, None

    state_nr_str = str(alliance.state)

    state_role = await services.database.get_guild_tags(tag='state.role', guild_id=guild_id, space=state_nr_str, limit=1)
    state_role = state_role[0] if len(state_role) > 0 else None

    if not state_role:
        state_role_instance = await guild.create_role(name=f'State {state_nr_str}', permissions=Permissions(0))
        await services.database.add_guild_tag(guild_id, str(state_role_instance.id), 'state.role', space=state_nr_str)

    alliance_id = str(alliance.id)

    ###################
    # BASE ROLE SETUP #
    ###################

    existing_base_role = await services.database.get_guild_tags(guild_id=guild_id, tag='alliance_role_base', space=alliance_id, limit=1)
    existing_base_role = existing_base_role[0] if len(existing_base_role) == 1 else None
    base_role = None

    if existing_base_role:
        try:
            role_id = int(existing_base_role.value)
            base_role = await guild.fetch_role(role_id)
        except Exception:
            pass

    role_name = f'{alliance.code} Member'
    if base_role: await base_role.edit(name=role_name)
    else: base_role = await guild.create_role(name=role_name, permissions=Permissions(0))

    if existing_base_role: await services.database.update_guild_tag(existing_base_role, value=str(base_role.id))
    else: existing_base_role = await services.database.add_guild_tag(guild_id, str(base_role.id), 'alliance_role_base', space=alliance_id)

    ##############################
    # JOIN REQUEST CHANNEL SETUP #
    ##############################

    existing_jrc = await services.database.get_guild_tags(guild_id=guild_id, tag='alliance_jrc', space=alliance_id, limit=1)
    existing_jrc = existing_jrc[0] if len(existing_jrc) == 1 else None

    alliance_jrc = None

    if existing_jrc:
        try:
            role_id = int(existing_jrc.value)
            _alliance_jrc = await guild.fetch_channel(role_id)
            if isinstance(_alliance_jrc, TextChannel):
                alliance_jrc = _alliance_jrc
        except Exception:
            pass

    join_requests_channel_name = f'{alliance.code.lower()}-join-requests'
    if alliance_jrc: await alliance_jrc.edit(name=join_requests_channel_name)
    else: alliance_jrc = await join_requests_category.create_text_channel(name=join_requests_channel_name)

    await alliance_jrc.set_permissions(base_role, overwrite=PermissionOverwrite(view_channel=True))

    if existing_jrc: await services.database.update_guild_tag(existing_jrc, value=str(alliance_jrc.id))
    else: existing_jrc = await services.database.add_guild_tag(guild_id, str(alliance_jrc.id), 'alliance_jrc', space=alliance_id)

    return base_role, existing_base_role, alliance_jrc, existing_jrc

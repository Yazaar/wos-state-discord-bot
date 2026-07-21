import time
from discord import Color, Embed, Guild, Interaction, ButtonStyle, CategoryChannel, Member
from discord.ui import Modal, TextInput, View, Button
from discordHandler import DiscordClient

from models.alliance import Alliance
from models.join_request import JoinInvite
from models.wos_link import WosLink
from services import get_services
from utils.wos_api_utils import WosPlayer, get_player
from utils.discord_utils import component_array_to_dict, auto_close_interaction_callback, find_text_channel_by_name, updated_embed
from utils.memory_cache import MemoryCache
from utils.async_utils import new_uuid

rate_limiter = MemoryCache(30)
wos_link_cache = MemoryCache(180)
wos_acc_cache = MemoryCache(180)

async def __find_wos_player(wos_player_id: int | str) -> WosPlayer | None:
    if isinstance(wos_player_id, str):
        try: wos_player_id = int(wos_player_id)
        except Exception: return None

    cache = wos_acc_cache.get(wos_player_id)
    if cache: return cache

    try: fetched = await get_player(wos_player_id)
    except Exception: return None

    if not fetched: return None

    wos_acc_cache.set(wos_player_id, fetched)
    return fetched

async def __handle_auth(
        client: DiscordClient, interaction: Interaction, alliance: Alliance,
        wos_player: WosPlayer, link_member: Member | None, join_invite: JoinInvite | None):
    guild = interaction.guild

    if not guild:
        await interaction.response.send_message('Unable to detect which server the interaction originates from', ephemeral=True)
        return

    wos_acc_embed = Embed(title='WOS account')
    wos_acc_embed.add_field(name='Name', value=wos_player.name, inline=False)
    wos_acc_embed.add_field(name='Furnace', value=wos_player.stove_lvl, inline=False)
    wos_acc_embed.add_field(name='State', value=wos_player.server, inline=False)
    if wos_player.avatar_img: wos_acc_embed.set_thumbnail(url=wos_player.avatar_img)

    if wos_player.server != alliance.state:
        await interaction.response.send_message('Sorry, but you are not in the alliance state', embed=wos_acc_embed, ephemeral=True)

    wos_alliance_embed = Embed(title='WOS alliance')
    wos_alliance_embed.add_field(name='Code', value=alliance.code, inline=False)
    wos_alliance_embed.add_field(name='Name', value=alliance.name, inline=False)

    view = View()

    callback = auto_close_interaction_callback(interaction)

    req_id = new_uuid()

    yes_btn = Button(label='Yes', style=ButtonStyle.green, custom_id=f'link_wos_acc.yes::{req_id}')
    no_btn = Button(label='No', style=ButtonStyle.red, custom_id='link_wos_acc.no')
    yes_btn.callback = callback
    no_btn.callback = callback
    view.add_item(yes_btn)
    view.add_item(no_btn)

    wos_link_cache.set(req_id, (wos_player, alliance, join_invite, link_member))

    await interaction.response.send_message('Please confirm the account and alliance is correct', embeds=[wos_acc_embed, wos_alliance_embed], view=view, ephemeral=True)

async def __check_wos_reserved(
        client: DiscordClient, interaction: Interaction, guild: Guild,
        wos_id: str, wos_name: str | None, allow_discord_id: str | None):
    services = get_services()
    wos_link = await services.database.get_wos_links(guild_id=str(guild.id), wos_id=wos_id, status='active', limit=1)
    wos_link = wos_link[0] if len(wos_link) > 0 else None

    if wos_link and wos_link.discord_id != allow_discord_id:
        try: taken_by_member = guild.get_member(int(wos_link.discord_id))
        except Exception: taken_by_member = None
        taken_by_sect = f'Discord member {taken_by_member.display_name} ({taken_by_member.name})' if taken_by_member else 'another Discord user'
        await interaction.response.send_message(
            f'Sorry, unable to link the WOS account {wos_name or wos_link.wos_name} due to how someone else ' +
            f'linked this WOS account previously to {taken_by_sect}. Reach out for help if you believe this is an error', ephemeral=True)
        return True, wos_link, taken_by_member

    return False, wos_link, None


async def __setup_alliance_link(
        client: DiscordClient, interaction: Interaction, discord_member: Member, player_data: WosPlayer,
        alliance: Alliance, wos_link: WosLink | None, *, join_invite: JoinInvite | None = None):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect the discord server for this interaction', ephemeral=True)
        return False

    services = get_services()

    guild_id = str(guild.id)

    state_role_tag = await services.database.get_guild_tags(guild_id=guild_id, space=str(player_data.server), tag='state.role', limit=1)
    state_role_tag = state_role_tag[0] if len(state_role_tag) > 0 else None

    try: state_role = guild.get_role(int(state_role_tag.value)) if state_role_tag else None
    except Exception: state_role = None

    if not state_role:
        await interaction.response.send_message('Unable to find the role associated to the WOS state', ephemeral=True)
        return False

    alliance_role_tag = await services.database.get_guild_tags(guild_id=guild_id, space=str(alliance.id), tag='alliance_role_base', limit=1)
    alliance_role_tag = alliance_role_tag[0] if len(alliance_role_tag) > 0 else None

    try: alliance_role = guild.get_role(int(alliance_role_tag.value)) if alliance_role_tag else None
    except Exception: alliance_role = None

    if not alliance_role:
        await interaction.response.send_message('Unable to find the role associated to the alliance', ephemeral=True)
        return False

    await discord_member.add_roles(alliance_role, state_role)

    try: await discord_member.edit(nick=f'[{alliance.code}] {player_data.name}')
    except Exception: pass

    if join_invite:
        await services.database.update_join_invite(join_invite, executed=True)

    if not wos_link:
        await services.database.register_wos_link(
            guild_id, str(discord_member.id),
            str(player_data.player_id), player_data.name
        )

    return True

async def tnc_alliance_join_request_click(client: DiscordClient, interaction: Interaction):
    modal = Modal(title='Request alliance to join', custom_id='tnc_alliance_join_req')
    account_id_field = TextInput(label='WOS account id', custom_id='wos_account_id', required=True)
    alliance_code = TextInput(label='Alliance code', custom_id='alliance_code', required=True)
    modal.add_item(account_id_field)
    modal.add_item(alliance_code)
    await interaction.response.send_modal(modal)

async def tnc_alliance_join_req(
        client: DiscordClient, interaction: Interaction,
        wos_acc_id: str | None = None, alliance_code: str | None = None, link_member: Member | None = None):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect which server the interaction was triggered from', ephemeral=True)
        return

    components = interaction.data.get('components', []) if interaction.data else []
    if not isinstance(components, list):
        await interaction.response.send_message('Unable to process your request due to unexpectedly data components missing', ephemeral=True)
        return

    properties = component_array_to_dict(components)
    wos_account_id_str = wos_acc_id or properties.get('wos_account_id', None)
    alliance_code = alliance_code or properties.get('alliance_code', None)

    if not isinstance(wos_account_id_str, str) or not wos_account_id_str:
        await interaction.response.send_message('WOS account id missing', ephemeral=True)
        return

    if not isinstance(alliance_code, str) or not alliance_code:
        await interaction.response.send_message('Alliance code missing', ephemeral=True)
        return

    try: wos_account_id = int(wos_account_id_str)
    except Exception:
        await interaction.response.send_message('WOS account id invalid', ephemeral=True)
        return

    wos_player = await __find_wos_player(wos_account_id)
    if not wos_player:
        await interaction.response.send_message('WOS account not found', ephemeral=True)
        return
    wos_acc_cache.set(wos_account_id, wos_player)

    limiter_key = f'join_req::{interaction.user.id}'
    rate_limit = rate_limiter.get(limiter_key, True) or 0
    if not isinstance(rate_limit, int) or rate_limit == 2:
        await interaction.response.send_message('Sorry you are rate limited', ephemeral=True)
        return
    rate_limiter.set(limiter_key, rate_limit + 1)

    services = get_services()
    alliance = await services.database.get_alliances(guild_id=str(guild.id), code=alliance_code, state=wos_player.server, limit=1)
    alliance = alliance[0] if len(alliance) == 1 else None
    if not alliance:
        await interaction.response.send_message('The provided alliance code is invalid', ephemeral=True)
        return

    await __handle_auth(client, interaction, alliance, wos_player, link_member, None)

async def accepted_join_invite(client: DiscordClient, interaction: Interaction, join_invite: JoinInvite, player_data: WosPlayer, alliance: Alliance):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect which guild this interaction originates from', ephemeral=True)
        return

    member = interaction.user
    if not isinstance(member, Member):
        await interaction.response.send_message('Unable to detect which member this interaction originates from', ephemeral=True)
        return

    is_reserved, wos_link, reserved_by = await __check_wos_reserved(
        client, interaction, guild, str(player_data.player_id),
        player_data.name, str(member.id)
    )
    if is_reserved: return

    success = await __setup_alliance_link(client, interaction, member, player_data, alliance, wos_link, join_invite=join_invite)
    if not success: return

    await interaction.response.send_message(f'Welcome, access granted to alliance *[{alliance.code}] {alliance.name}*!', ephemeral=True)

async def link_wos_acc_yes(client: DiscordClient, interaction: Interaction, req_id: str):
    try:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message('Unable to detect the discord server for this interaction', ephemeral=True)
            return

        guild_id = str(guild.id)

        cache_data = wos_link_cache.get(req_id)
        if not cache_data:
            await interaction.response.send_message('Sorry command expired, please try again', ephemeral=True)
            return
        wos_link_cache.remove(req_id)

        if not isinstance(cache_data, tuple) or not len(cache_data) == 4:
            await interaction.response.send_message('Command data unexpected length, please try again', ephemeral=True)
            return

        player_data, alliance, join_invite, link_member = cache_data
        if not isinstance(player_data, WosPlayer) or not isinstance(alliance, Alliance) or alliance.guild_id != guild_id:
            await interaction.response.send_message('Command data unexpected types, please try again', ephemeral=True)
            return

        link_member = link_member if link_member else interaction.user
        if not isinstance(link_member, Member):
            await interaction.response.send_message('Unable to detect the target member for this interaction within the discord server', ephemeral=True)
            return

        if isinstance(join_invite, JoinInvite):
            await accepted_join_invite(client, interaction, join_invite, player_data, alliance)
            return

        services = get_services()
        tag = await services.database.get_guild_tags(tag='join-req.category', guild_id=alliance.guild_id)
        tag = tag[0] if tag else None
        if not tag:
            await interaction.response.send_message('Unable to complete request due to join missing requests missing setup', ephemeral=True)
            return

        try:
            if not tag.value: raise Exception('Channel id is None')
            tag_channel = int(tag.value)
        except Exception:
            await interaction.response.send_message('Invalid format registered for the server\'s join request target', ephemeral=True)
            return

        channel = guild.get_channel(tag_channel)
        if not isinstance(channel, CategoryChannel):
            await interaction.response.send_message('Join request target is linked to an invalid target for the server', ephemeral=True)
            return

        alliance_code_lower = alliance.code.lower()
        join_request_channel = find_text_channel_by_name(f'{alliance_code_lower}-join-requests', channel.channels)
        if not join_request_channel:
            await interaction.response.send_message('Unable to find the join request text channel for the specific alliance', ephemeral=True)
            return

        member_id_str = str(link_member.id)
        wos_id_str = str(player_data.player_id)

        result = await services.database.find_latest_join_request(member_id_str, wos_id_str, alliance.id)

        wos_link = await services.database.get_wos_links(guild_id=guild_id, wos_id=wos_id_str, status='active', limit=1)
        wos_link = wos_link[0] if len(wos_link) else None

        if wos_link and wos_link.discord_id != member_id_str:
            try: taken_by_member = guild.get_member(int(wos_link.discord_id))
            except Exception: taken_by_member = None
            taken_by_sect = f'Discord member {taken_by_member.display_name} ({taken_by_member.name})' if taken_by_member else 'another Discord user'
            await interaction.response.send_message(
                f'Sorry, unable to link the WOS account {player_data.name} due to how someone else ' +
                f'linked this WOS account previously to {taken_by_sect}. Reach out for help if you believe this is an error', ephemeral=True)
            return

        if result:
            current_time = time.time()
            time_diff = current_time - result.timestamp
            if time_diff < 3600:
                await interaction.response.send_message(
                    f'You recently requested to join the alliance *[{alliance.code}] {alliance.name}* and is therefore on cooldown before being able to re-apply',
                    ephemeral=True
                )
                return

        join_request_entity = await services.database.register_join_request(
            member_id_str, link_member.name, link_member.global_name or link_member.display_name,
            wos_id_str, player_data.name, alliance.id
        )

        embedDiscordAcc = Embed(title='Discord account', color=Color.yellow())
        embedDiscordAcc.add_field(name='Username', value=link_member.name, inline=False)
        embedDiscordAcc.add_field(name='Discord nickname', value=link_member.global_name or link_member.name, inline=False)
        embedDiscordAcc.add_field(name='Server nickname', value=link_member.display_name, inline=False)
        if link_member.avatar and link_member.avatar.url: embedDiscordAcc.set_thumbnail(url=link_member.avatar.url)

        embedWosAcc = Embed(title='WOS account', color=Color.yellow())
        embedWosAcc.add_field(name='Name', value=player_data.name, inline=False)
        embedWosAcc.add_field(name='Furnace', value=player_data.stove_lvl, inline=False)
        if player_data.avatar_img: embedWosAcc.set_thumbnail(url=player_data.avatar_img)

        view = View()
        accept = Button(label='Accept', style=ButtonStyle.green, custom_id=f'join_request_accept::{join_request_entity.id}')
        reject = Button(label='Reject', style=ButtonStyle.red, custom_id=f'join_request_reject::{join_request_entity.id}')
        view.add_item(accept)
        view.add_item(reject)

        join_req_msg = await join_request_channel.send(
            f'New request to join the {alliance.code} alliance by {link_member.display_name} ({link_member.name}) / {player_data.name}',
            view=view, embeds=[embedDiscordAcc, embedWosAcc]
        )

        await services.database.update_join_request(join_request_entity, discord_message_id=str(join_req_msg.id))

        await interaction.response.send_message(f'Join request sent to alliance *[{alliance.code}] {alliance.name}*', ephemeral=True)
    except Exception as e:
        print('Failed to handle link_wos_acc_yes', str(e))

async def tnc_code_join_click(client: DiscordClient, interaction: Interaction):
    modal = Modal(title='Request alliance to join', custom_id='tnc_invite_code_req')
    account_id_field = TextInput(label='WOS account id', custom_id='wos_account_id', required=True)
    invite_code = TextInput(label='Invite code', custom_id='invite_code', required=True)
    modal.add_item(account_id_field)
    modal.add_item(invite_code)
    await interaction.response.send_modal(modal)

async def link_wos_acc_accept(client: DiscordClient, interaction: Interaction, request_id: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect which server this interaction is associated with', ephemeral=True)
        return

    handler = interaction.user
    if not isinstance(handler, Member):
        await interaction.response.send_message(
            'Unable to process the join request due to the following reason\n\n' +
            '> Unable to detect which member triggered the interaction', ephemeral=True
        )
        return

    services = get_services()
    join_request = await services.database.get_join_requests(id_=request_id, limit=1)
    join_request = join_request[0] if len(join_request) > 0 else None

    if not join_request:
        await interaction.response.send_message('Unable to accept member since the join request can not be found.\n\n' +
            '> You may work around this by manually assigning the alliance role to this member', ephemeral=True)
        return

    try: discord_member = guild.get_member(int(join_request.discord_id))
    except Exception: discord_member = None

    if not discord_member:
        await interaction.response.send_message('Unable find the discord member this join request is associated with', ephemeral=True)
        return

    is_reserved, wos_link, reserved_by = await __check_wos_reserved(
        client, interaction, guild, join_request.wos_id,
        join_request.wos_username, join_request.discord_id
    )

    if is_reserved:
        return

    alliance = await services.database.get_alliances(id_=join_request.wos_alliance_id, limit=1)
    alliance = alliance[0] if len(alliance) > 0 else None
    if not alliance:
        await interaction.response.send_message('Unable find the alliance this join request is associated with', ephemeral=True)
        return

    try: wos_player = await __find_wos_player(join_request.wos_id)
    except Exception: wos_player = None

    if not wos_player:
        await interaction.response.send_message('Unable find the WOS player this join request is associated with', ephemeral=True)
        return

    success = await __setup_alliance_link(client, interaction, discord_member, wos_player, alliance, wos_link)
    if not success:
        return

    if interaction.message:
        await interaction.message.edit(embeds=updated_embed(interaction.message.embeds, color=Color.green()), view=None)

    try: await discord_member.send(f'**[{guild.name}]** You have been accepted to the alliance, welcome to *[{alliance.code}] {alliance.name}*!')
    except Exception:
        await interaction.response.send_message(
            'Join request accepted, but was unable to notify the member due to the following reason\n\n' +
            '> Failed to send DM to member', ephemeral=True
        )
        return

    await interaction.response.send_message(
        f'Join request accepted for {discord_member.display_name} ({discord_member.name}) and member been notified over DMs',
        ephemeral=True
    )

async def link_wos_acc_reject(client: DiscordClient, interaction: Interaction, request_id: str):
    handler = interaction.user
    if not isinstance(handler, Member):
        await interaction.response.send_message(
            'Unable to process the join request due to the following reason\n\n' +
            '> Unable to detect which member triggered the interaction', ephemeral=True
        )
        return

    if interaction.message:
        await interaction.message.edit(embeds=updated_embed(interaction.message.embeds, color=Color.red()), view=None)

    services = get_services()
    join_request = await services.database.get_join_requests(id_=request_id, limit=1)
    join_request = join_request[0] if len(join_request) > 0 else None

    if not join_request:
        await interaction.response.send_message(
            'Join request rejected, but was unable to notify the member due to the following reason\n\n' +
            '> The referenced join request could not be found in the system', ephemeral=True
        )
        return

    await services.database.update_join_request(join_request, status='rejected', handler_discord_id=str(handler.id))

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message(
            'Join request rejected, but was unable to notify the member due to the following reason\n\n' +
            '> Unable to detect which server this interaction originates from', ephemeral=True
        )
        return

    try: discord_member = guild.get_member(int(join_request.discord_id))
    except Exception: discord_member = None

    if not discord_member:
        await interaction.response.send_message(
            'Join request rejected, but was unable to notify the member due to the following reason\n\n' +
            '> Discord member not found', ephemeral=True
        )
        return

    alliance = await services.database.get_alliances(id_=join_request.wos_alliance_id, limit=1)
    alliance = alliance[0] if len(alliance) > 0 else None

    if not alliance:
        await interaction.response.send_message(
            'Join request rejected, but was unable to notify the member due to the following reason\n\n' +
            '> Alliance not found', ephemeral=True
        )
        return

    try: await discord_member.send(f'**[{guild.name}]** Unfortunately you have been rejected to join *[{alliance.code}] {alliance.name}*')
    except Exception:
        await interaction.response.send_message(
            'Join request rejected, but was unable to notify the member due to the following reason\n\n' +
            '> Failed to send DM to member', ephemeral=True
        )
        return

    await interaction.response.send_message(
        f'Join request rejected for {discord_member.display_name} ({discord_member.name}) and member been notified over DMs',
        ephemeral=True
    )

async def tnc_invite_code_req(client: DiscordClient, interaction: Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message(
            'Unable to process the join request due to the following reason\n\n' +
            '> Unable to detect which guild the interaction originates from', ephemeral=True
        )
        return

    member = interaction.user
    if not isinstance(member, Member):
        await interaction.response.send_message(
            'Unable to process the join request due to the following reason\n\n' +
            '> Unable to detect which member triggered the interaction', ephemeral=True
        )
        return

    if not interaction.data:
        await interaction.response.send_message('Unable to process your request due to unexpectedly data missing', ephemeral=True)
        return

    components = interaction.data.get('components', None)
    if not isinstance(components, list):
        await interaction.response.send_message('Unable to process your request due to unexpectedly data components missing', ephemeral=True)
        return

    properties = component_array_to_dict(components)
    wos_account_id = properties.get('wos_account_id', None)
    invite_code = properties.get('invite_code', None)

    try:
        if not wos_account_id: raise Exception()
        wos_account_id = int(wos_account_id)
    except Exception:
        await interaction.response.send_message(
            'Unable to process the join request due to the following reason\n\n' +
            '> The provided WOS account id is of an invalid format', ephemeral=True
        )
        return

    if not invite_code:
        await interaction.response.send_message(
            'Unable to process the join request due to the following reason\n\n' +
            '> The provided invite code is invalid', ephemeral=True
        )
        return

    limiter_key = f'join_req::{interaction.user.id}'
    rate_limit = rate_limiter.get(limiter_key, True) or 0
    if not isinstance(rate_limit, int) or rate_limit == 2:
        await interaction.response.send_message('Sorry you are rate limited', ephemeral=True)
        return
    rate_limiter.set(limiter_key, rate_limit + 1)

    services = get_services()
    join_invite = await services.database.get_join_invite(invite_code=invite_code, executed=False, limit=1)
    join_invite = join_invite[0] if len(join_invite) > 0 else None

    if not join_invite:
        await interaction.response.send_message(
            'Unable to process the join request due to the following reason\n\n' +
            '> The provided invite code could not be found', ephemeral=True
        )
        return

    wos_player = await __find_wos_player(wos_account_id)
    if not wos_player:
        await interaction.response.send_message('WOS account not found', ephemeral=True)
        return

    alliance = await services.database.get_alliances(id_=join_invite.wos_alliance_id, state=wos_player.server, limit=1)
    alliance = alliance[0] if len(alliance) > 0 else None

    if not alliance:
        await interaction.response.send_message(
            'Unable to process the join request due to the following reason\n\n' +
            '> Unable to find the alliance bound to the invite code', ephemeral=True
        )
        return

    await __handle_auth(client, interaction, alliance, wos_player, None, join_invite)

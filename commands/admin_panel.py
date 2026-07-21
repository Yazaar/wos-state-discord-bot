from services import get_services
from utils.discord_utils import auto_close_interaction_callback, component_array_to_dict
from utils.app_utils import paged_list
from discordHandler import DiscordClient
from discord import ButtonStyle, CategoryChannel, Color, Embed, Interaction, Member, TextChannel
from discord.ui import View, Button, Select, Modal, TextInput
import typing
from .admin_panel_alliance_manage import alliance_create, alliance_remove

if typing.TYPE_CHECKING:
    from discord.guild import GuildChannel
    from discord.interactions import InteractionChannel

def __allowed_manage_channel(member: Member, channel: 'GuildChannel'):
    perms = channel.permissions_for(member)
    return perms.administrator or perms.manage_channels

def __is_visible(member: Member, channel: 'GuildChannel'):
    perms = channel.permissions_for(member)
    return perms.administrator or perms.view_channel

async def __create_txt_selector(
        page: int,
        comp_id: str,
        member: Member,
        interaction_channel: 'InteractionChannel | None',
        guild_channels: typing.Sequence['GuildChannel'],
        include_check: typing.Callable[[Member, 'GuildChannel'], bool],
        default_select_channel: int | None):
    channel_selector = Select(custom_id=comp_id)

    selector_channels: list[TextChannel] = []

    default_channel: TextChannel | None = None

    for channel in guild_channels:
        if (
            (not interaction_channel or interaction_channel.id != channel.id) and
            isinstance(channel, TextChannel) and
            include_check(member, channel)
        ):
            if default_select_channel == channel.id: default_channel = channel
            else: selector_channels.append(channel)

    selector_channels.sort(key=lambda x: x.name)

    if isinstance(interaction_channel, TextChannel) and include_check(member, interaction_channel):
        selector_channels.insert(0, interaction_channel)

    if default_channel: selector_channels.insert(0, default_channel)

    selector_channels, last_page = paged_list(selector_channels, 20, page)

    for channel in selector_channels:
        channel_selector.add_option(label=channel.name, value=str(channel.id), default=default_select_channel == channel.id)

    if last_page != 0:
        if page > 0: channel_selector.add_option(label='Prev page', value=f'SETPAGE::{page-1}')
        if page != last_page: channel_selector.add_option(label='Next page', value=f'SETPAGE::{page+1}')

    return channel_selector

async def __create_cat_selector(
        page: int,
        comp_id: str,
        member: Member,
        interaction_channel: 'InteractionChannel | None',
        guild_channels: typing.Sequence['GuildChannel'],
        include_check: typing.Callable[[Member, 'GuildChannel'], bool],
        default_select_channel: int | None):
    channel_selector = Select(custom_id=comp_id)

    selector_channels: list[CategoryChannel] = []
    default_channel: CategoryChannel | None = None

    for channel in guild_channels:
        if (
            isinstance(channel, CategoryChannel) and
            include_check(member, channel)
        ):
            if default_select_channel == channel.id: default_channel = channel
            else: selector_channels.append(channel)

    selector_channels.sort(key=lambda x: x.name)

    if default_channel:
        selector_channels.insert(0, default_channel)

    selector_channels, last_page = paged_list(selector_channels, 20, page)

    for channel in selector_channels:
        channel_selector.add_option(label=channel.name, value=str(channel.id), default=default_select_channel == channel.id)

    if last_page != 0:
        if page > 0: channel_selector.add_option(label='Prev page', value=f'SETPAGE::{page-1}')
        if page != last_page: channel_selector.add_option(label='Next page', value=f'SETPAGE::{page+1}')

    return channel_selector

async def __generic_selector_handler(
        client: DiscordClient,
        interaction: Interaction,
        embed_title: str,
        embed_desc: str,
        selector_id: str,
        selector_getter: typing.Callable[[int, str, Member, 'InteractionChannel | None', typing.Sequence['GuildChannel'], typing.Callable[[Member, 'GuildChannel'], bool], int | None], typing.Awaitable[Select]],
        page_num: int,
        selector_include_check: typing.Callable[[Member, 'GuildChannel'], bool],
        default_select_db_key: str | None
):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect what server the interaction came from', ephemeral=True)
        return

    member = interaction.user
    if not isinstance(member, Member):
        await interaction.response.send_message('Unable to detect what member triggered the interaction', ephemeral=True)
        return

    embed = Embed(title=embed_title, description=embed_desc)

    view = View()

    default_select_id: int | None = None

    if default_select_db_key:
        services = get_services()
        tags = await services.database.get_guild_tags(guild_id=str(guild.id), tag=default_select_db_key, limit=1)
        if len(tags) == 1 and tags[0].value:
            try: default_select_id = int(tags[0].value)
            except Exception: pass

    channel_selector = await selector_getter(page_num, selector_id, member, interaction.channel, guild.channels, selector_include_check, default_select_id)
    channel_selector.callback = auto_close_interaction_callback(interaction)
    view.add_item(channel_selector)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def __generic_selected_handler(client: DiscordClient, interaction: Interaction, success_msg: str, db_channel_key: str):
    if not isinstance(interaction.data, dict):
        await interaction.response.send_message('Event data is missing', ephemeral=True)
        return

    values = interaction.data.get('values', None)
    if not isinstance(values, list) or len(values) < 1:
        await interaction.response.send_message('Event data values is missing', ephemeral=True)
        return
    
    if values[0].startswith('SETPAGE::'):
        custom_id = interaction.data.get('custom_id', None)
        try: page = int(values[0][9:])
        except Exception:
            await interaction.response.send_message('Invalid pagination', ephemeral=True)
            return
        if custom_id == 'admin_panel.set_gcc':
            await set_gcc_show_selector(client, interaction, str(page))
        elif custom_id == 'admin_panel.set_tncc':
            await set_tncc_show_selector(client, interaction, str(page))
        elif custom_id == 'admin_panel.set_jrc':
            await set_jrc_show_selector(client, interaction, str(page))
        elif custom_id == 'admin_panel.set_invite_channel':
            await set_invite_channel_opt(client, interaction, str(page))
        else:
            await interaction.response.send_message('Unknown command type', ephemeral=True)
        return

    try: target_channel_id = int(values[0])
    except Exception:
        await interaction.response.send_message('Provided channel is of an invalid format', ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect which server this interaction originates from', ephemeral=True)
        return

    target_channel = guild.get_channel(target_channel_id)
    if not target_channel:
        await interaction.response.send_message('Unable to find the selection on the current server', ephemeral=True)
        return

    services = get_services()
    await services.database.add_unique_guild_tag(str(guild.id), str(target_channel.id), db_channel_key)
    await interaction.response.send_message(
        success_msg + (f'*{target_channel.name}*' if isinstance(target_channel, CategoryChannel) else target_channel.mention),
        ephemeral=True
    )

async def set_jrc_selected(client: DiscordClient, interaction: Interaction):
    await __generic_selected_handler(client, interaction, 'Join requests bound to ', 'join-req.category')

async def set_tncc_selected(client: DiscordClient, interaction: Interaction):
    await __generic_selected_handler(client, interaction, 'Terms & conditions bound to ', 'tnc_channel')

async def set_gcc_selected(client: DiscordClient, interaction: Interaction):
    await __generic_selected_handler(client, interaction, 'Giftcodes bound to ', 'giftcode_channel')

async def set_gcc_show_selector(client: DiscordClient, interaction: Interaction, page: str = '0'):
    try: page_num = int(page)
    except Exception: page_num = 0

    await __generic_selector_handler(
        client,
        interaction,
        'Set giftcode channel',
        'Select which channel giftcodes should be sent to',
        'admin_panel.set_gcc',
        __create_txt_selector,
        page_num,
        __allowed_manage_channel,
        'giftcode_channel'
    )

async def set_tncc_show_selector(client: DiscordClient, interaction: Interaction, page: str = '0'):
    try: page_num = int(page)
    except Exception: page_num = 0

    await __generic_selector_handler(
        client,
        interaction,
        'Set Terms & Conditions channel',
        'Select which channel terms & conditions should be sent to',
        'admin_panel.set_tncc',
        __create_txt_selector,
        page_num,
        __allowed_manage_channel,
        'tnc_channel'
    )

# jrc = join request category
async def set_jrc_show_selector(client: DiscordClient, interaction: Interaction, page: str = '0'):
    try: page_num = int(page)
    except Exception: page_num = 0

    await __generic_selector_handler(
        client,
        interaction,
        'Set join request category',
        'Select which category is used for alliance join requests',
        'admin_panel.set_jrc',
        __create_cat_selector,
        page_num,
        __allowed_manage_channel,
        'join-req.category'
    )

async def create_tncd(client: DiscordClient, interaction: Interaction):
    channel = interaction.channel
    if not isinstance(channel, TextChannel):
        await interaction.response.send_message('Unable to detect what text channel the interaction came from', ephemeral=True)
        return

    lines = [
        '# Bot Terms & Conditions dashboard',
        f'*Server: {channel.guild.name}*' if channel.guild else '',
        '## Reactions',
        '- `📜 Release existing terms and conditions draft`',
        '- `📝 Create a new terms and conditions draft`'
    ]

    lines = [line for line in lines if line]

    button_activate_tnc_draft = Button(label='📜', style=ButtonStyle.gray, custom_id='button_activate_tnc_draft')
    button_create_tnc_draft = Button(label='📝', style=ButtonStyle.gray, custom_id='button_create_tnc_draft')
    view = View()
    view.add_item(button_activate_tnc_draft)
    view.add_item(button_create_tnc_draft)
    await interaction.response.send_message(content='\n'.join(lines), view=view)

async def manage_state_whitelist(client: DiscordClient, interaction: Interaction):
    view = View()
    auto_close = auto_close_interaction_callback(interaction)
    add_btn = Button(label='Add state', style=ButtonStyle.gray, custom_id='admin_panel.add_state_selector')
    remove_btn = Button(label='Remove state', style=ButtonStyle.gray, custom_id='admin_panel.remove_state_selector')
    add_btn.callback = auto_close
    remove_btn.callback = auto_close

    view.add_item(add_btn)
    view.add_item(remove_btn)

    await interaction.response.send_message('State management: Select what you would like to do\n\n> Tip: list states by the remove function', view=view, ephemeral=True)

async def manage_state_whitelist_add_selector(client: DiscordClient, interaction: Interaction):
    modal = Modal(title='Whitelist state', custom_id='admin_panel.add_state')
    state_input = TextInput(label='State number', custom_id='state_number')
    modal.add_item(state_input)
    await interaction.response.send_modal(modal)

async def manage_state_whitelist_add(client: DiscordClient, interaction: Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect which server the interaction originates from', ephemeral=True)
        return

    if not isinstance(interaction.data, dict):
        await interaction.response.send_message('Event data is missing', ephemeral=True)
        return

    components = interaction.data.get('components')
    if not isinstance(components, list):
        await interaction.response.send_message('Event data is missing', ephemeral=True)
        return

    comp_items = component_array_to_dict(components)

    state_number_str = comp_items.get('state_number', None)
    if not state_number_str:
        await interaction.response.send_message('State number missing', ephemeral=True)
        return

    try: state_number = int(state_number_str)
    except Exception:
        await interaction.response.send_message('State number is an invalid format (expected number)', ephemeral=True)
        return

    services = get_services()
    await services.database.whitelist_state_add(str(guild.id), str(state_number))
    await interaction.response.send_message(f'State {state_number} is now allowed to join the server', ephemeral=True)

async def manage_state_whitelist_remove_selector(client: DiscordClient, interaction: Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect the server which this interaction originates from', ephemeral=True)
        return

    services = get_services()
    state_list = await services.database.whitelist_state_list(str(guild.id))
    max_item_len = len(max(state_list, key=len, default=''))
    state_list.sort(key=lambda x: x.zfill(max_item_len))

    if len(state_list) == 0:
        await interaction.response.send_message('No states found', ephemeral=True)
        return

    view = View()
    state_selector = Select(custom_id='admin_panel.remove_state')
    for state in state_list: state_selector.add_option(label=state, value=state)
    view.add_item(state_selector)
    await interaction.response.send_message('Select the state you would like to remove', view=view, ephemeral=True)

async def manage_state_whitelist_remove(client: DiscordClient, interaction: Interaction):
    if not isinstance(interaction.data, dict):
        await interaction.response.send_message('Event data is missing', ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect the server which this interaction originates from', ephemeral=True)
        return

    values = interaction.data.get('values', None)
    if not isinstance(values, list) or len(values) < 1:
        await interaction.response.send_message('Event data values is missing', ephemeral=True)
        return

    try: target_state = int(values[0])
    except Exception:
        await interaction.response.send_message('Provided state is of an invalid format', ephemeral=True)
        return

    services = get_services()
    await services.database.whitelist_state_remove(str(guild.id), str(target_state))

    await interaction.response.send_message(f'Players from state {target_state} is no longer allowed on to the server', ephemeral=True)

async def manage_alliance_whitelist(client: DiscordClient, interaction: Interaction):
    view = View()
    auto_close = auto_close_interaction_callback(interaction)
    add_btn = Button(label='Add alliance', style=ButtonStyle.gray, custom_id='admin_panel.add_alliance_selector')
    remove_btn = Button(label='Remove alliance', style=ButtonStyle.gray, custom_id='admin_panel.remove_alliance_selector')
    add_btn.callback = auto_close
    remove_btn.callback = auto_close

    view.add_item(add_btn)
    view.add_item(remove_btn)

    await interaction.response.send_message('State management: Select what you would like to do\n\n> Tip: list states by the remove function', view=view, ephemeral=True)

async def manage_alliance_whitelist_add_selector(client: DiscordClient, interaction: Interaction):
    modal = Modal(title='Whitelist alliance', custom_id='admin_panel.add_alliance')
    code_input = TextInput(label='Alliance code', custom_id='alliance_code')
    name_input = TextInput(label='Alliance name', custom_id='alliance_name')
    state_input = TextInput(label='Alliance state', custom_id='alliance_state')
    modal.add_item(code_input)
    modal.add_item(name_input)
    modal.add_item(state_input)
    await interaction.response.send_modal(modal)

async def manage_alliance_whitelist_add(client: DiscordClient, interaction: Interaction):
    if not isinstance(interaction.data, dict):
        await interaction.response.send_message('Event data is missing', ephemeral=True)
        return

    components = interaction.data.get('components')
    if not isinstance(components, list):
        await interaction.response.send_message('Event data components is missing', ephemeral=True)
        return

    comp_items = component_array_to_dict(components)

    alliance_name = comp_items.get('alliance_name', None)
    alliance_code = comp_items.get('alliance_code', None)
    alliance_state = comp_items.get('alliance_state', None)

    try:
        if not alliance_state: raise Exception('Invalid alliance state')
        alliance_state = int(alliance_state)
    except Exception:
        await interaction.response.send_message('The provided alliance state is invalid', ephemeral=True)
        return

    if not alliance_name or not alliance_code:
        await interaction.response.send_message('Event data values is missing', ephemeral=True)
        return

    await alliance_create(client, interaction, alliance_code, alliance_name, alliance_state)

async def manage_alliance_whitelist_remove_selector(client: DiscordClient, interaction: Interaction):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect the server which this interaction originates from', ephemeral=True)
        return

    services = get_services()
    alliance_list = await services.database.get_alliances(guild_id=str(guild.id))
    alliance_list.sort(key=lambda x: x.code)

    if len(alliance_list) == 0:
        await interaction.response.send_message('No alliances found', ephemeral=True)
        return
    
    view = View()
    alliance_selector = Select(custom_id='admin_panel.remove_alliance')
    alliance_selector.callback = auto_close_interaction_callback(interaction)
    for alliance in alliance_list:
        alliance_selector.add_option(label=f'[{alliance.code}] {alliance.name} ({alliance.state})', value=str(alliance.id))
    view.add_item(alliance_selector)
    await interaction.response.send_message('Select the alliance you would like to remove', view=view, ephemeral=True)

async def manage_alliance_whitelist_remove(client: DiscordClient, interaction: Interaction):
    if not isinstance(interaction.data, dict):
        await interaction.response.send_message('Event data is missing', ephemeral=True)
        return

    values = interaction.data.get('values', None)
    if not isinstance(values, list) or len(values) < 1:
        await interaction.response.send_message('Event data values is missing', ephemeral=True)
        return

    await alliance_remove(client, interaction, values[0])

async def set_invite_channel_opt(client: DiscordClient, interaction: Interaction, page: str = '0'):
    try: page_num = int(page)
    except Exception: page_num = 0

    await __generic_selector_handler(
        client,
        interaction,
        'Set invite channel',
        'Select which channel bot created invite links should target',
        'admin_panel.set_invite_channel',
        __create_txt_selector,
        page_num,
        __is_visible,
        'invite_channel')

async def set_invite_channel(client: DiscordClient, interaction: Interaction):
    await __generic_selected_handler(client, interaction, 'Invite links bound to ', 'invite_channel')

async def admin_panel(client: DiscordClient, interaction: Interaction):
    try:
        member = interaction.user
        if not isinstance(member, Member):
            await interaction.response.send_message('Unable to detect what member triggered the interaction', ephemeral=True)
            return

        guild = interaction.guild
        if not guild:
            await interaction.response.send_message('Unable to detect what server the interaction came from', ephemeral=True)
            return

        view = View()

        auto_close_callback = auto_close_interaction_callback(interaction)

        txt_selector = await __create_txt_selector(0, 'x', member, interaction.channel, guild.channels, __allowed_manage_channel, None)
        cat_selector = await __create_cat_selector(0, 'x', member, interaction.channel, guild.channels, __allowed_manage_channel, None)

        manage_txt_count = len(txt_selector.options)
        manage_cat_count = len(cat_selector.options)

        if member.guild_permissions.administrator:
            btn = Button(label='Manage alliance whitelist', custom_id='admin_panel.opt.alliance_whitelist')
            btn.callback = auto_close_callback
            view.add_item(btn)

            btn = Button(label='Set invite channel', custom_id='admin_panel.opt.set_invite_channel')
            btn.callback = auto_close_callback
            view.add_item(btn)

        if manage_txt_count > 0:
            btn = Button(label='Set giftcode channel', custom_id='admin_panel.opt.set_gcc')
            btn.callback = auto_close_callback
            view.add_item(btn)

            btn = Button(label='Set T&C channel', custom_id='admin_panel.opt.set_tncc')
            btn.callback = auto_close_callback
            view.add_item(btn)

            btn = Button(label='Create T&C dashboard here', custom_id='admin_panel.opt.create_tncd')
            btn.callback = auto_close_callback
            view.add_item(btn)

        if manage_cat_count > 0:
            btn = Button(label='Set join request category', custom_id='admin_panel.opt.set_jrc')
            btn.callback = auto_close_callback
            view.add_item(btn)

        if view.total_children_count == 0:
            await interaction.response.send_message('You are missing permission for any administration tools', ephemeral=True)
            return

        embed = Embed(title='Bot administration panel', description='You are allowed to take the following actions via the ' +
                    'administration panel in the current channel\n\n**⚠️ WARNING: Be cautious**', color=Color.green())

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    except Exception as e:
        print('Failed to handle admin_panel:', str(e))

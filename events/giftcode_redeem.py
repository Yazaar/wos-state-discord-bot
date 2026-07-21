import time
from io import BytesIO
from discord import File, Interaction, Member
from discordHandler import DiscordClient
from services import get_services
from discord.ui import Select, View, Button, Modal, TextInput
from tickers.giftcodes import process_expired_giftcodes, process_valid_giftcodes
from utils.discord_utils import auto_close_interaction_callback, component_array_to_dict
from utils.wos_api_utils import get_player, get_captcha, redeem_code

async def handle_redeem_finalize(client: DiscordClient, interaction: Interaction, code: str, wos_account_id_str: str):
    try: wos_account_id = int(wos_account_id_str)
    except Exception:
        await interaction.response.send_message('Invalid player id', ephemeral=True)
        return

    if not isinstance(interaction.data, dict):
        await interaction.response.send_message('Event data is missing', ephemeral=True)
        return

    components = interaction.data.get('components')
    if not isinstance(components, list):
        await interaction.response.send_message('Event data is missing', ephemeral=True)
        return

    comp_items = component_array_to_dict(components)

    captcha_value = comp_items.get('captcha_value', None)
    if not isinstance(captcha_value, str):
        await interaction.response.send_message('Captcha value is missing', ephemeral=True)
        return

    result = await redeem_code(wos_account_id, code, captcha_value)

    if result == 'used':
        await interaction.response.send_message('Already redeemed', ephemeral=True)
        await process_valid_giftcodes([code])
    elif result == 'redeemed':
        await interaction.response.send_message('Redeemed successfully', ephemeral=True)
        await process_valid_giftcodes([code])
    elif result == 'expired':
        await interaction.response.send_message(f'The giftcode {code} has unfortunately already expired', ephemeral=True)
        await process_expired_giftcodes([code], close=True)
    elif result == 'not-found':
        await interaction.response.send_message(f'The giftcode {code} does not exist', ephemeral=True)
    else:
        await interaction.response.send_message(f'Unknown WOS system giftcode status detected: `{result}`', ephemeral=True)

async def handle_redeem_captcha_prompt(client: DiscordClient, interaction: Interaction, code: str, wos_account_id: str):
    modal = Modal(title='Giftcode captcha', custom_id=f'giftcode.captcha::{code}::{wos_account_id}')
    captcha_input = TextInput(label='Captcha value', custom_id=f'captcha_value', required=True)
    modal.add_item(captcha_input)
    await interaction.response.send_modal(modal)

async def handle_redeem(client: DiscordClient, interaction: Interaction, code: str, wos_account_id_str: str):
    try: wos_account_id = int(wos_account_id_str)
    except Exception:
        await interaction.response.send_message('The linked WOS account id is of an unexpected format', ephemeral=True)
        return

    try: await get_player(wos_account_id)
    except Exception:
        await interaction.response.send_message('Failed to load the WOS account', ephemeral=True)
        return

    try:
        wos_captcha = await get_captcha(wos_account_id)
        if not wos_captcha: raise Exception('Invalid captcha')
    except Exception:
        await interaction.response.send_message('Failed to generate a WOS redeem captcha for the account', ephemeral=True)
        return

    view = View()
    refresh_captcha = Button(label='Refresh captcha', custom_id=f'giftcode.refresh::{code}::{wos_account_id}')
    enter_captcha = Button(label='Enter captcha', custom_id=f'giftcode.solve::{code}::{wos_account_id}')

    refresh_captcha.callback = auto_close_interaction_callback(interaction)

    view.add_item(refresh_captcha)
    view.add_item(enter_captcha)

    captcha_file = BytesIO(wos_captcha)

    await interaction.response.send_message(
        'In order to process the giftcode please solve the following captcha from WOS',
        view=view, ephemeral=True,
        file=File(fp=captcha_file, filename=f'wos-captcha-{time.time_ns()}.png')
    )

async def giftcode_redeem_by_click(client: DiscordClient, interaction: Interaction, code: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect which server the interaction originates from', ephemeral=True)
        return

    if not interaction.data:
        await interaction.response.send_message('The selection data is missing', ephemeral=True)
        return

    values = interaction.data.get('values', None)
    if not isinstance(values, list):    
        await interaction.response.send_message('The selection data is in an unexpected format', ephemeral=True)
        return

    try: account_id = int(values[0])
    except Exception:
        await interaction.response.send_message('The selected account is in an unexpected format', ephemeral=True)
        return

    services = get_services()
    wos_link = await services.database.get_wos_links(id_=account_id, limit=1)
    wos_link = wos_link[0] if len(wos_link) > 0 else None
    if not wos_link or wos_link.guild_id != str(guild.id):
        await interaction.response.send_message('The selected account does not match any existing accounts for the current server', ephemeral=True)
        return

    await handle_redeem(client, interaction, code, wos_link.wos_id)

async def giftcode_redeem_click(client: DiscordClient, interaction: Interaction, code: str):
    member = interaction.user
    if not isinstance(member, Member):
        await interaction.response.send_message('Unable to detect what member clicked the button', ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect what server the interaction originates from', ephemeral=True)
        return

    services = get_services()
    wos_accounts = await services.database.get_wos_links(guild_id=str(guild.id), discord_id=str(member.id), status='active')

    if len(wos_accounts) == 0:
        await interaction.response.send_message('You have no wos accounts linked', ephemeral=True)
        return

    view = View()
    select = Select(custom_id=f'giftcode.redeem.by::{code}')
    select.callback = auto_close_interaction_callback(interaction)

    for acc in wos_accounts:
        select.add_option(label=acc.wos_name, value=str(acc.id))

    view.add_item(select)
    await interaction.response.send_message('Please select the WOS account to redeem for', view=view, ephemeral=True)

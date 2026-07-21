from io import BytesIO
from discord import File, Interaction
from discord.ui import View, Button, Modal, TextInput
import time
from discordHandler import DiscordClient
from utils.discord_utils import component_array_to_dict, auto_close_interaction_callback
from utils.wos_api_utils import get_captcha, get_player, redeem_code

async def giftcode_add(client: DiscordClient, interaction: Interaction, code: str):
    view = View()
    refresh_captcha = Button(label='Refresh captcha', custom_id=f'gcc.refresh::{code}')
    enter_captcha = Button(label='Enter captcha', custom_id=f'gcc.solve::450490453::{code}')

    refresh_captcha.callback = auto_close_interaction_callback(interaction)

    view.add_item(refresh_captcha)
    view.add_item(enter_captcha)

    await get_player(450490453)
    captcha = await get_captcha(450490453)

    if not captcha:
        await interaction.response.send_message('Unable to interact with the internals of Whiteout Survival...', ephemeral=True)
        return

    captcha_file = BytesIO(captcha)

    await interaction.response.send_message(
        'In order to add the gift code please solve the following captcha',
        view=view, ephemeral=True,
        file=File(fp=captcha_file, filename=f'wos-captcha-{time.time()}.png')
    )

async def giftcode_add_solve(client: DiscordClient, interaction: Interaction, player_id_str: str, code: str):
    modal = Modal(title='Giftcode captcha', custom_id=f'gcc.input::{player_id_str}::{code}')
    captcha_input = TextInput(label='Captcha value', custom_id=f'captcha_value', required=True)
    modal.add_item(captcha_input)

    await interaction.response.send_modal(modal)

async def giftcode_add_input(client: DiscordClient, interaction: Interaction, player_id_str: str, giftcode: str):
    try: player_id = int(player_id_str)
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

    result = await redeem_code(player_id, giftcode, captcha_value)

    if result == 'used' or result == 'redeemed':
        pass
    elif result == 'expired':
        await interaction.response.send_message(f'The giftcode {giftcode} has unfortunately already expired', ephemeral=True)
        return
    elif result == 'not-found':
        await interaction.response.send_message(f'The giftcode {giftcode} does not exist', ephemeral=True)
        return
    else:
        await interaction.response.send_message(f'Unknown WOS system giftcode status detected: `{result}`', ephemeral=True)
        return

    await interaction.response.send_message('Redeemed successfully', ephemeral=True)

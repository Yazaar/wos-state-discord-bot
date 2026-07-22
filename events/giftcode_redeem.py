from discord import Interaction, Member
from discordHandler import DiscordClient
from services import get_services
from discord.ui import Select, View
from tickers.giftcodes import process_expired_giftcodes, process_valid_giftcodes
from utils.discord_utils import auto_close_interaction_callback
from utils.wos_api_utils import redeem_code

async def handle_redeem(client: DiscordClient, interaction: Interaction, code: str, wos_account_id_str: str):
    try: wos_account_id = int(wos_account_id_str)
    except Exception:
        await interaction.response.send_message('The linked WOS account id is of an unexpected format', ephemeral=True)
        return

    result = await redeem_code(wos_account_id, code, 2844)

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
        await interaction.response.send_message('The selected account does not match any existing accounts', ephemeral=True)
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

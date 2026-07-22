from discord import Interaction
from discordHandler import DiscordClient
from models.wos_link import WosLink
from services import get_services
from tickers.giftcodes import process_valid_giftcodes
from utils.discord_utils import auto_close_interaction_callback
from utils.wos_api_utils import redeem_code

async def giftcode_add(client: DiscordClient, interaction: Interaction, code: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message(f'Unable to detect discord server', ephemeral=True)
        return

    member = interaction.user

    services = get_services()

    wos_link = await services.database.get_wos_links(guild_id=str(guild.id), discord_id=str(member.id), status='active')

    for i in wos_link:
        if i.alliance_id:
            wos_link = i
            break

    if not isinstance(wos_link, WosLink):
        await interaction.response.send_message(f'Unable to find a connected WOS account with an alliance', ephemeral=True)
        return  

    alliance = await services.database.get_alliances(id_=wos_link.alliance_id, limit=1)
    alliance = alliance[0] if len(alliance) == 1 else None
    if not alliance:
        await interaction.response.send_message(f'WOS account bound to unknown alliance', ephemeral=True)
        return  

    try: wos_id = int(wos_link.wos_id)
    except Exception:
        await interaction.response.send_message(f'WOS account id is invalid', ephemeral=True)
        return

    result = await redeem_code(wos_id, code, alliance.state)

    if result == 'used' or result == 'redeemed':
        await interaction.response.send_message(f'Giftcode `{code}` valid and added, thank you for your contribution!', ephemeral=True)
        await process_valid_giftcodes([code])
    elif result == 'expired':
        await interaction.response.send_message(f'The giftcode `{code}` has unfortunately already expired', ephemeral=True)
    elif result == 'not-found':
        await interaction.response.send_message(f'The giftcode `{code}` does not exist', ephemeral=True)
    else:
        await interaction.response.send_message(f'Unknown WOS system giftcode status detected: `{result}`', ephemeral=True)

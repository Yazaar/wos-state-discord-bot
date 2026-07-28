import io
from discord import Guild, Member, File
from discord.interactions import Interaction
from discordHandler import DiscordClient
from models.alliance import Alliance
from models.wos_link import WosLink
from services import get_services
from utils.wos_api_utils import test_wos_account

async def verify_user(client: DiscordClient, interaction: Interaction, wos_account_id: str, wos_state_number: str):
    try: wos_account_id_int = int(wos_account_id)
    except Exception:
        await interaction.response.send_message('`wos_account_id` have to be a number', ephemeral=True)
        return
    
    try: wos_state_number_int = int(wos_state_number)
    except Exception:
        await interaction.response.send_message('`wos_state_number` have to be a number', ephemeral=True)
        return

    is_valid = await test_wos_account(wos_account_id_int, wos_state_number_int)

    if is_valid: await interaction.response.send_message(f'✅ `{wos_account_id_int}` detected to be in state `{wos_state_number_int}`', ephemeral=True)
    else: await interaction.response.send_message(f'❌ `{wos_account_id_int}` not detected in state `{wos_state_number_int}`', ephemeral=True)

async def verify_account(client: DiscordClient, interaction: Interaction, member: Member, allowed_state_numbers: str | None):
    try:
        guild = interaction.guild

        try: state_list_allowed = [int(i.strip()) for i in allowed_state_numbers.split(',')] if allowed_state_numbers else None
        except Exception:
            await interaction.response.send_message(f'All provided state numbers have to be numbers!', ephemeral=True)
            return

        if not guild:
            await interaction.response.send_message('Discord server not detected', ephemeral=True)
            return
        
        services = get_services()

        alliance_results: dict[int, Alliance] = dict()

        wos_links = await services.database.get_wos_links(guild_id=str(guild.id), discord_id=str(member.id))
        for wos_link in wos_links:
            try: wos_user_id = int(wos_link.wos_id)
            except Exception: continue

            state_numbers_check = state_list_allowed
            if not state_numbers_check:
                if not wos_link.alliance_id: continue
                alliance_cache = alliance_results.get(wos_link.alliance_id, None)
                if not alliance_cache:
                    alliance_cache = await services.database.get_alliances(id_=wos_link.alliance_id, limit=1)
                    alliance_cache = alliance_cache[0] if len(alliance_cache) == 1 else None
                    if alliance_cache: alliance_results[alliance_cache.id] = alliance_cache

                if not alliance_cache: continue

                try: state_numbers_check = [int(alliance_cache.state)]
                except Exception: continue

            for state_number in state_numbers_check:
                is_valid = await test_wos_account(wos_user_id, state_number)
                if is_valid:
                    await interaction.response.send_message(f'✅ Member is in state {state_number} with account `{wos_user_id}` ({wos_link.wos_name})', ephemeral=True)
                    return

        await interaction.response.send_message(f'❌ Member not detected in state', ephemeral=True)
    except Exception as e:
        print('Unable to handle verify_account:', str(e))

async def verify_all_users(client: DiscordClient, interaction: Interaction):
    try:
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message('Discord server not detected', ephemeral=True)
            return

        services = get_services()
        wos_links = await services.database.get_wos_links(guild_id=str(guild.id), status='active')

        invalid_links: list[WosLink] = []
        unknown_links: list[WosLink] = []

        alliance_results: dict[int, Alliance] = dict()

        await interaction.response.send_message('Verifying all users...', ephemeral=True)

        for wos_link in wos_links:
            try: await guild.fetch_member(int(wos_link.discord_id)) # check if discord id still is in the Discord server
            except Exception: continue
            
            try: wos_user_id = int(wos_link.wos_id)
            except Exception:
                unknown_links.append(wos_link)
                continue

            if not wos_link.alliance_id:
                unknown_links.append(wos_link)
                continue

            alliance = alliance_results.get(wos_link.alliance_id, None)
            if not alliance:
                alliance = await services.database.get_alliances(id_=wos_link.alliance_id, limit=1)
                alliance = alliance[0] if len(alliance) == 1 else None
                if alliance: alliance_results[alliance.id] = alliance

            if not alliance:
                unknown_links.append(wos_link)
                continue

            is_valid = await test_wos_account(wos_user_id, alliance.state)

            if not is_valid:
                invalid_links.append(wos_link)

        response_text = 'Invalid:\n'
        for i in invalid_links: response_text += await create_user_text_line(guild, i, alliance_results)
        if len(invalid_links) == 0: response_text += 'No invalid accounts!\n'

        response_text += '\nUnknown status:\n'
        for i in unknown_links: response_text += await create_user_text_line(guild, i, alliance_results)
        if len(unknown_links) == 0: response_text += 'No unknown accounts!\n'
        response_text = response_text.strip()

        if len(response_text) > 2000:
            file_data = io.BytesIO(response_text.encode('utf-8'))
            file = File(fp=file_data, filename="output.txt")
            await interaction.edit_original_response(content='Data too large for text message, see provided file', attachments=[file])
        else:
            await interaction.edit_original_response(content=response_text)

    except Exception as e:
        print('Unable to handle verify_all_users:', str(e))


async def create_user_text_line(guild: Guild, wos_link: WosLink, alliance_cache: dict[int, Alliance]):
        alliance_desc = ''
        alliance = alliance_cache.get(wos_link.alliance_id, None) if wos_link.alliance_id else None
        if alliance: alliance_desc = f' - [{alliance.code}] {alliance.name} ({alliance.state})'

        try: discord_acc = await guild.fetch_member(int(wos_link.discord_id))
        except Exception: discord_acc = None

        discord_desc = f'{discord_acc.name if discord_acc else 'n/a'} ({wos_link.discord_id})'

        return f'{discord_desc} - {wos_link.wos_name} ({wos_link.wos_id}){alliance_desc}\n'

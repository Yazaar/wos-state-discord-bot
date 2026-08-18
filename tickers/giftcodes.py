import aiohttp, datetime, random, time as time_module, re
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from discord import Color, Embed, TextChannel
from discord.ui import View, Button
from models.giftcode import Giftcode
from services import Services, get_services
from utils.discord_utils import updated_embed

# 30 days
AUTO_CLOSE_TIME = 30 * 24 * 60 * 60

next_process = 0

directory = Path(__file__).parent
time_file = directory / 'giftcodes_next_check.txt'

def get_next_check_time():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    current_hour = now_utc.hour

    # Format: [start_hour, end_hour, gen_min_hour, gen_max_hour, days_diff]
    rules = [
        [0, 14, 15, 21, 0],  # If 00:00-14:59, gen tonight 15:00-21:00 (Today)
        [15, 23, 6, 12, 1]   # If 15:00-23:59, gen tomorrow 06:00-12:00 (Tomorrow)
    ]

    for start, end, gen_min, gen_max, days_diff in rules:
        if start <= current_hour and current_hour <= end:
            target_date = now_utc + datetime.timedelta(days=days_diff)

            target_time = target_date.replace(
                hour=random.randint(gen_min, gen_max),
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
                microsecond=0
            )

            return int(target_time.timestamp())

    return int((now_utc + datetime.timedelta(days=1)).timestamp())

##############################
# https://www.wosrewards.com #
##############################

def detect_giftcode_wosrewards(tag: Tag, code_type: str):
    tag_parent = tag.parent
    if not tag_parent or tag_parent.get_text(strip=True) != code_type:
        return None

    giftcode_card = tag_parent.parent
    if not giftcode_card: return None

    giftcode_element = giftcode_card.find('h5')
    if not giftcode_element: return None

    giftcode = giftcode_element.get_text(strip=True)
    if not giftcode: return None
    return giftcode

async def load_src_wosrewards():
    headers = {
        ':authority': 'www.wosrewards.com',
        ':method': 'GET',
        ':path': '/giftcodes',
        ':scheme': 'https',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'en;q=0.7,en-US;q=0.6',
        'cache-control': 'no-cache',
        'dnt': '1',
        'pragma': 'no-cache',
        'priority': 'u=0, i',
        'referer': 'https://www.wosrewards.com/',
        'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36'
    }

    async with aiohttp.ClientSession() as session:
        async with session.get('https://www.wosrewards.com/giftcodes', headers=headers) as resp:
            html = await resp.text()

    soup = BeautifulSoup(html, "lxml")

    valid_giftcodes: list[str] = []
    expired_giftcodes: list[str] = []

    active_codes_title = soup.find('div', string='Active Codes')
    if active_codes_title:
        active_codes_wrapper = active_codes_title.find_next('div')
        if active_codes_wrapper:
            active_codes_buttons = soup.select('button[data-code]')
            for active_code_btn in active_codes_buttons:
                active_code = active_code_btn['data-code'].strip()
                if active_code: valid_giftcodes.append(active_code)

    done = False
    for span in soup.select('details > summary > span'):
        text = span.get_text(strip=True)
        if re.match(r'\d+ expired codes', text):
            done = True
            invalid_codes_wrapper = span.parent.find_next('div')
            if invalid_codes_wrapper:
                for invalid_code_element in invalid_codes_wrapper.select('div > div > div > div.line-through'):
                    invalid_code = invalid_code_element.get_text(strip=True)
                    expired_giftcodes.append(invalid_code)
                    if len(expired_giftcodes) > 9:
                        break

            if done: break

    valid_giftcodes.reverse()
    expired_giftcodes.reverse()

    return valid_giftcodes, expired_giftcodes

################################
# https://www.wosgiftcodes.com #
################################

def detect_giftcode_wosgiftcodes(tag: Tag, code_type: str) -> list[str]:
    if not tag or tag.get_text(strip=True) != code_type:
        return []

    tag_parent = tag.parent
    if not tag_parent: return []

    tag_parent_parent = tag_parent.parent
    if not tag_parent_parent: return []

    thead = tag_parent_parent.find('thead')
    if not thead: return []

    ths = thead.find_all('th')
    if not ths: return []

    code_index = -1
    for i in range(len(ths)):
        thead_tr = ths[i]
        if thead_tr.get_text(strip=True).lower() == 'code':
            code_index = i
            break

    if code_index == -1: return []

    tbody = tag_parent_parent.find('tbody')
    if not tbody: return []

    giftcodes: list[str] = []
    trs = tbody.find_all('tr')
    for tr in trs:
        tds = tr.find_all('td')
        if len(tds) <= code_index: continue
        giftcode = tds[code_index].get_text(strip=True)
        if giftcode: giftcodes.append(giftcode)

    return giftcodes

async def load_src_wosgiftcodes():
    async with aiohttp.ClientSession() as session:
        async with session.get('https://www.wosgiftcodes.com') as resp:
            html = await resp.text()

    soup = BeautifulSoup(html, "lxml")

    active_giftcodes: list[str] = []
    expired_giftcodes: list[str] = []

    h5s = soup.find_all('h5')
    for h5 in h5s:
        table_giftcodes = detect_giftcode_wosgiftcodes(h5, 'Active Codes')
        for tg in table_giftcodes:
            active_giftcodes.append(tg)

    for h5 in h5s:
        table_giftcodes = detect_giftcode_wosgiftcodes(h5, 'Expired Codes')
        for tg in table_giftcodes:
            expired_giftcodes.append(tg)
            if len(expired_giftcodes) > 9:
                break

    active_giftcodes.reverse()
    expired_giftcodes.reverse()
    return active_giftcodes, expired_giftcodes

################################
# https://www.wosgiftcodes.com #
################################

async def get_giftcodes():
    valid_giftcodes: list[str] = []
    expired_giftcodes: list[str] = []

    try:
        valid, expired = await load_src_wosrewards()
        for i in valid:
            if not i in valid_giftcodes:
                valid_giftcodes.append(i)
        for i in expired:
            if not i in expired_giftcodes:
                expired_giftcodes.append(i)
    except Exception as e:
        print('Failed to load wosrewards_codes', str(e))

    try:
        valid, expired = await load_src_wosgiftcodes()
        for i in valid:
            if not i in valid_giftcodes:
                valid_giftcodes.append(i)
        for i in expired:
            if not i in expired_giftcodes:
                expired_giftcodes.append(i)
    except Exception as e:
        print('Failed to load wosgiftcodes_codes', str(e))

    return (valid_giftcodes, [i for i in expired_giftcodes if not i in valid_giftcodes])

async def get_giftcode_channels(services: Services):
    channels: list[TextChannel] = []
    tags = await services.database.get_guild_tags(tag='giftcode_channel')

    for tag in tags:
        if not tag.value: continue
        try: guild_id = int(tag.guild_id)
        except Exception: continue
        try: channel_id = int(tag.value)
        except Exception: continue

        guild = services.discord.get_guild(guild_id)
        if not guild: continue

        try: channel = await guild.fetch_channel(channel_id)
        except Exception: continue

        if not isinstance(channel, TextChannel): continue
        channels.append(channel)

    return channels

async def process_expired_giftcodes(expired_codes: list[str], current_time: float | None = None, close: bool = False):
        time = int(current_time or time_module.time())
        services = get_services()
        active_codes_db = await services.database.get_active_giftcodes()
        expired_codes_db: list[Giftcode] = []

        for i in active_codes_db:
            if i.code in expired_codes:
                expired_codes_db.append(i)

        for to_expire_code in expired_codes_db:
            if close or (to_expire_code.expiry_date and time - to_expire_code.expiry_date > AUTO_CLOSE_TIME):
                await services.database.update_giftcode(to_expire_code, expiry_date=to_expire_code.expiry_date or time, close_date=time)
                await update_giftcode_message(to_expire_code, Color.red(), True, services)
            elif not to_expire_code.expiry_date:
                await services.database.update_giftcode(to_expire_code, expiry_date=time)
                await update_giftcode_message(to_expire_code, Color.yellow(), False, services)

async def update_giftcode_message(giftcode: Giftcode, color: Color | None, remove_buttons: bool, services: Services):
    db_messages = await services.database.get_giftcode_messages(giftcode_id=giftcode.id)

    for db_message in db_messages:
        try: guild_id = int(db_message.guild_id)
        except Exception: continue
        try: channel_id = int(db_message.channel_id)
        except Exception: continue
        try: message_id = int(db_message.message_id)
        except Exception: continue
        guild = services.discord.get_guild(guild_id)
        if not guild: continue
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, TextChannel): continue
        try: message = await channel.fetch_message(message_id)
        except Exception: continue

        args = {}
        if color: args['embeds'] = updated_embed(message.embeds, color=color)
        if remove_buttons: args['view'] = None

        try: await message.edit(**args)
        except Exception as e:
            print('failed to update giftcode message', str(e))

async def process_valid_giftcodes(valid_codes: list[str], current_time: float | None = None):
        time = int(current_time or time_module.time())
        services = get_services()

        existing = await services.database.get_giftcodes_by_code(valid_codes)

        existing_codes = [i.code for i in existing if not i.expiry_date]
        new_codes = [code for code in valid_codes if not code in existing_codes]

        giftcode_channels = None

        if len(new_codes) == 0:
            return

        giftcode_channels = await get_giftcode_channels(services)

        embed = Embed(
            color=Color.green(),
            title='Giftcode detected'
        )

        embed.add_field(name='', value='✅ I have redeemed this code', inline=False)
        embed.add_field(name='', value='❌ Code did not work', inline=False)

        for new_code in new_codes:
            giftcode_entity = await services.database.register_giftcode(new_code, int(time))
            for channel in giftcode_channels:
                view = View()
                view.add_item(Button(label='⭐ Redeem', custom_id=f'giftcode.redeem::{new_code}'))
                try: message = await channel.send(content=new_code, embed=embed, view=view)
                except Exception: continue
                await services.database.register_giftcode_message(giftcode_entity.id, str(channel.guild.id), str(channel.id), str(message.id))
                await message.add_reaction('✅')
                await message.add_reaction('❌')

async def init():
    global next_process
    if not time_file.is_file():
        return

    try:
        with open(time_file, 'r', encoding='utf8') as f: file_time_str = f.read()
        file_time = int(file_time_str)
        next_process = file_time
    except Exception: pass

async def tick(time: float):
    try:
        global next_process
        if time < next_process:
            return

        next_process = get_next_check_time()

        with open(time_file, 'w', encoding='utf8') as f:
            f.write(str(next_process))

        valid_codes, expired_codes = await get_giftcodes()

        await process_valid_giftcodes(valid_codes, time)
        await process_expired_giftcodes(expired_codes)

    except Exception as e:
        print('failed to process giftcodes tick:', str(e))

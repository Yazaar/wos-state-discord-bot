import base64, asyncio
import time, hashlib
import aiohttp

class WosPlayer:
    def __init__(self, player_id: int, name: str, server: int, stove_lvl: int, avatar_img: str):
        self.player_id = player_id
        self.name = name
        self.server = server
        self.stove_lvl = stove_lvl
        self.avatar_img = avatar_img

def __sign(text: str) -> str:
    return hashlib.md5((text + 'tB87#kPtkxqOS2').encode('utf-8')).hexdigest()

async def get_captcha(player_id: int):
    timestamp = int(time.time() * 1000)

    form = f"fid={player_id}&init=0&time={timestamp}"
    sign = __sign(form)
    body = f'sign={sign}&{form}'

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "sv-SE,sv;q=0.9,en-SE;q=0.8,en;q=0.7,en-US;q=0.6",
        "content-type": "application/x-www-form-urlencoded",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-gpc": "1",
        "Referer": "https://wos-giftcode.centurygame.com/"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post('https://wos-giftcode-api.centurygame.com/api/captcha', data=body, headers=headers) as resp:
            resp_payload = await resp.json()

    if not isinstance(resp_payload, dict): return None
    resp_data = resp_payload.get('data', None)
    if not isinstance(resp_data, dict): return None
    resp_img = resp_data.get('img', None)
    if not isinstance(resp_img, str): return None

    img_parts = resp_img.split(',', 1)

    if len(img_parts) != 2: return None
    img_data = img_parts[1]

    try: image_bytes = base64.b64decode(img_data)
    except Exception: return None

    return image_bytes

async def get_player(player_id: int):
    timestamp = int(time.time() * 1000)

    form = f'fid={player_id}&time={timestamp}'
    sign = __sign(form)
    body = f'sign={sign}&{form}'

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "sv-SE,sv;q=0.9,en-SE;q=0.8,en;q=0.7,en-US;q=0.6",
        "content-type": "application/x-www-form-urlencoded",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-gpc": "1",
        "Referer": "https://wos-giftcode.centurygame.com/"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post('https://wos-giftcode-api.centurygame.com/api/player', data=body, headers=headers) as resp:
                resp_res = await resp.json()
    except Exception:
        return None

    if not isinstance(resp_res, dict): return None
    resp_data = resp_res.get('data', None)
    if not isinstance(resp_data, dict): return None

    player_id_ = resp_data.get('fid', None)
    name = resp_data.get('nickname', None)
    server = resp_data.get('kid', None)
    stove_lvl = resp_data.get('stove_lv', None)
    avatar_img = resp_data.get('avatar_image', None)

    if not isinstance(player_id_, int) or not isinstance(name, str) or not isinstance(server, int) or not isinstance(stove_lvl, int) or not isinstance(avatar_img, str):
        return None

    return WosPlayer(player_id_, name, server, stove_lvl, avatar_img)

async def redeem_code(player_id: int, giftcode: str, captcha_code: str):
    timestamp = int(time.time() * 1000)

    form = f'captcha_code={captcha_code}&cdk={giftcode}&fid={player_id}&time={timestamp}'
    sign = __sign(form)
    body = f'sign={sign}&{form}'

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "sv-SE,sv;q=0.9,en-SE;q=0.8,en;q=0.7,en-US;q=0.6",
        "content-type": "application/x-www-form-urlencoded",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Not(A:Brand\";v=\"8\", \"Chromium\";v=\"144\", \"Google Chrome\";v=\"144\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-gpc": "1",
        "Referer": "https://wos-giftcode.centurygame.com/"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post('https://wos-giftcode-api.centurygame.com/api/gift_code', data=body, headers=headers) as resp:
            resp_payload = await resp.json()

    if not isinstance(resp_payload, dict): return None

    resp_msg = resp_payload.get('msg', None)
    if not isinstance(resp_msg, str): return None

    if resp_payload.get('code', None) == 0: return 'redeemed'
    elif resp_msg == 'TIME ERROR.': return 'expired'
    elif resp_msg == 'RECEIVED.': return 'used'
    elif resp_msg == 'CDK NOT FOUND.': return 'not-found'
    return resp_msg or 'unknown'

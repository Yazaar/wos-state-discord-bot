import asyncio
import random
import time, hashlib, string
import aiohttp

def __sign(text: str) -> str:
    return hashlib.md5((text + 'tB87#kPtkxqOS2').encode('utf-8')).hexdigest()

async def redeem_code(player_id: int, giftcode: str, state_number: int):
    timestamp = int(time.time())

    form = f'cdk={giftcode}&fid={player_id}&kid={state_number}&time={timestamp}'
    sign = __sign(form)
    body = f'sign={sign}&{form}'

    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "sv-SE,sv;q=0.9,en-SE;q=0.8,en;q=0.7,en-US;q=0.6",
        "content-type": "application/x-www-form-urlencoded",
        "priority": "u=1, i",
        "sec-ch-ua": "\"Not;A=Brand\";v=\"8\", \"Chromium\";v=\"150\", \"Google Chrome\";v=\"150\"",
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
    elif resp_msg == 'USER INFO ERROR.': return 'invalid-user'

    print(f'Unknown redeem code: {resp_msg}')
    return resp_msg or 'unknown'

async def test_wos_account(player_id: int, state_number: int):
    random_code = ''.join(
        random.choices(string.ascii_letters + string.digits, k=10)
    )

    result = await redeem_code(player_id, random_code, state_number)
    return result in ['redeemed', 'expired', 'used', 'not-found']

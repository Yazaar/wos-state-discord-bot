import asyncio, time
from . import giftcodes

async def setup():
    await asyncio.gather(giftcodes.init())

    while True:
        current_time = time.time()
        await asyncio.gather(giftcodes.tick(current_time))
        await asyncio.sleep(60)
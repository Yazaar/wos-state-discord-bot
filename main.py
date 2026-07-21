import asyncio
from discordHandler import DiscordClient
from database.get_db import get_db
from services import Services, set_services
import commands.setup
import events.setup
import tickers.setup
import app_commands.setup

async def main():
    database = await get_db()
    if not database: raise Exception('No database initialized')
    await database.startup()

    discord = DiscordClient()
    services = Services(database, discord)
    set_services(services)

    await events.setup.setup()
    await commands.setup.setup()
    await app_commands.setup.setup()
    await discord.start()
    await discord.wait_until_synced()
    await tickers.setup.setup()
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())

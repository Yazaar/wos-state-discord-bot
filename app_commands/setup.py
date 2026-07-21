from services import get_services
from app_commands.find_wos_account import find_wos_account, find_wos_account_public

async def setup():
    services = get_services()
    await services.discord.add_app_command('Find WOS account (private)', None, find_wos_account)
    await services.discord.add_app_command('Find WOS account (public)', None, find_wos_account_public)

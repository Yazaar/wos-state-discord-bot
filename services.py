import typing
if typing.TYPE_CHECKING:
    from database.db_shared import DatabaseInterface
    from discordHandler import DiscordClient

class Services:
    def __init__(self, database: 'DatabaseInterface', discord: 'DiscordClient'):
        self.database = database
        self.discord = discord

__INSTANCE: Services | None = None


def set_services(services: Services):
    global __INSTANCE
    __INSTANCE = services

def get_services():
    if not __INSTANCE: raise Exception('Services not initialized')
    return __INSTANCE

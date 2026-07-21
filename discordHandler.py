import os, typing, asyncio, inspect
import discord.ext.commands

UserAppCommand = typing.Callable[['DiscordClient', discord.Interaction, discord.User], typing.Awaitable[None]]
MessageAppCommand = typing.Callable[['DiscordClient', discord.Interaction, discord.Message], typing.Awaitable[None]]

class DiscordCommandOption:
    def __init__(self, name: str, description: str, option_type: str | type, optional: bool):

        self.name = name
        self.description = description        
        self.option_type = self.__parse_option_type(option_type)
        self.optional = optional

    def __parse_option_type(self, option_type: str | type):
        if isinstance(option_type, str):
            return option_type
        module_name_str = option_type.__module__
        option_type_str = option_type.__name__
        if module_name_str == 'builtins': module_name_str = ''
        else: module_name_str += '.'

        return f'{module_name_str}{option_type_str}'

class DiscordClient:
    def __init__(self):
        intents = discord.Intents.all()
        self.__bot = discord.ext.commands.Bot('!', intents=intents)
        self.__bot.add_listener(self.__trigger_on_ready, 'on_ready')
        self._synced_event = asyncio.Event()

    async def start(self):
        discord_token = os.environ.get('WOSBOT_DISCORD_TOKEN')
        if not discord_token: raise Exception('Discord token not found, env: WOSBOT_DISCORD_TOKEN')
        asyncio.create_task(self.__bot.start(discord_token))

    def get_self_user(self):
        user = self.__bot.user
        if not user: raise Exception('Not signed into Discord')
        return user

    def get_guilds(self):
        return self.__bot.guilds

    def get_guild(self, guild_id: int):
        return self.__bot.get_guild(guild_id)

    def __bake_event(self, func):
        async def inner(*args):
            await func(self, *args)
        return inner

    def __get_discord_baker(self, args: list[DiscordCommandOption]) -> typing.Callable:
        namespace = {}
        parsed_args = ''
        parsed_call = ''

        for i in args:
            parsed_args += f', {i.name}: {i.option_type}'
            if i.optional:
                parsed_args += f' = None'
            parsed_call += f', {i.name}'

        str_baker = f'''
def discord_command_baker(func, client):
    async def discord_command(interaction: discord.Interaction{parsed_args}):
        await func(client, interaction{parsed_call})
    return discord_command
'''

        exec(str_baker, globals(), namespace)

        return namespace.get('discord_command_baker') # type: ignore

    async def on_ready(self, func):
        self.__bot.add_listener(self.__bake_event(func), 'on_ready')

    async def wait_until_synced(self):
        await self._synced_event.wait()

    async def __trigger_on_ready(self):
        print('[discordHandler] ready')
        await self.__bot.tree.sync()
        print('[discordHandler] synced')
        self._synced_event.set()

    async def on_guild_channel_update(self, func):
        self.__bot.add_listener(self.__bake_event(func), 'on_guild_channel_update')

    async def on_vc_state(self, func):
        self.__bot.add_listener(self.__bake_event(func), 'on_voice_state_update')

    async def on_message(self, func):
        self.__bot.add_listener(self.__bake_event(func), 'on_message')

    async def on_permanent_reaction_add(self, func):
        self.__bot.add_listener(self.__bake_event(func), 'on_raw_reaction_add')

    async def on_reaction_add(self, func):
        self.__bot.add_listener(self.__bake_event(func), 'on_reaction_add')

    async def on_interaction(self, func):
        self.__bot.add_listener(self.__bake_event(func), 'on_interaction')

    async def add_slash_command(
            self,
            name: str,
            description: str,
            options: list[DiscordCommandOption],
            permissions: discord.Permissions | None,
            func
        ):
        baker = self.__get_discord_baker(options)
        wrapper = baker(func, self)

        command = discord.app_commands.command(name=name, description=description)(wrapper)
        command = discord.app_commands.describe(**{i.name: i.description for i in options})(command)
        if permissions:
            command = discord.app_commands.default_permissions(permissions)(command)

        self.__bot.tree.add_command(command)

    async def add_app_command(self, name: str, permissions: discord.Permissions | None, func: MessageAppCommand | UserAppCommand):
        sig = inspect.signature(func)
        params = list(sig.parameters)

        if len(params) != 3:
            raise Exception('App commands require the following parameters. (DiscordClient, Interaction, discord.Message/discord.User)')

        app_command_type = sig.parameters[params[2]].annotation        
        if app_command_type == discord.User:
            baker = self.__get_discord_baker([DiscordCommandOption('user', 'n/a', discord.User, False)])
        elif app_command_type == discord.Message:
            baker = self.__get_discord_baker([DiscordCommandOption('user', 'n/a', discord.Message, False)])
        else:
            raise Exception('Invalid app command type')

        wrapper = baker(func, self)
        command = discord.app_commands.ContextMenu(name=name, callback=wrapper)
        if permissions: command = discord.app_commands.default_permissions(permissions)(command)
        self.__bot.tree.add_command(command)

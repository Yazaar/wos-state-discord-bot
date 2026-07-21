from commands.create_age_counter import create_age_counter, get_days_since
from commands.create_alliance_invite import create_alliance_invite
from commands.admin_panel import admin_panel
from commands.nickname_manager import set_all_nicknames, set_nickname
from commands.remote_wos_link import remote_wos_link
from commands.wos_link_manager import refresh_link_selector, remove_link_selector
from discordHandler import DiscordCommandOption
from services import get_services
from .giftcode_add import giftcode_add
from .find_account import find_account, search_wos_account
from discord import Member, Permissions, TextChannel

async def setup():
    services = get_services()

    await services.discord.add_slash_command('giftcode_add', 'Add a new giftcode', [DiscordCommandOption('code', 'The in-game giftcode', str, False)], None, giftcode_add)

    await services.discord.add_slash_command('admin_panel', 'Show admin panel', [], None, admin_panel)

    await services.discord.add_slash_command('create_alliance_invite', 'Create a direct invite for an alliance', [], None, create_alliance_invite)

    await services.discord.add_slash_command('find_account', 'Search for a linked Discord/WOS account', [
        DiscordCommandOption('discord', 'Discord member', Member, True),
        DiscordCommandOption('wos_id', 'WOS id', str, True),
        DiscordCommandOption('wos_name', 'WOS name', str, True),
        DiscordCommandOption('public', 'Send with the value 1 to make command response public', str, True)
    ], None, find_account)

    await services.discord.add_slash_command('search_wos_account', 'Search for an existing WOS account', [
        DiscordCommandOption('wos_id', 'WOS id', str, False),
        DiscordCommandOption('public', 'Send with the value 1 to make command response public', str, True)
    ], None, search_wos_account)

    await services.discord.add_slash_command('create_date_counter', 'Create a message showing the time diff', [
        DiscordCommandOption('target_date', 'Target date in format YYYY-MM-DD', str, False),
        DiscordCommandOption('target_message', 'Edit an existing message from the bot into the age counter', str, True),
        DiscordCommandOption('target_channel', 'Select which channel to send the message in', TextChannel, True),
        DiscordCommandOption('title', 'Add a title to the message embed', str, True),
        DiscordCommandOption('description', 'Add a description to the message embed', str, True),
    ], Permissions(manage_channels=True, manage_messages=True), create_age_counter)

    await services.discord.add_slash_command('get_days_since', 'Displays how many days since something is', [
        DiscordCommandOption('target_date', 'Target date in format YYYY-MM-DD', str, False),
        DiscordCommandOption('public', 'Set to "1" if you want it to be a public message', str, True)
    ], None, get_days_since)

    await services.discord.add_slash_command('refresh_link', 'Refresh a linked WOS account', [
        DiscordCommandOption('member', 'Member to update if not yourself', Member, True)
    ], None, refresh_link_selector)

    await services.discord.add_slash_command('remove_link', 'Remove a linked WOS account', [
        DiscordCommandOption('member', 'Member to update if not yourself', Member, True)
    ], Permissions(manage_roles=True), remove_link_selector)

    await services.discord.add_slash_command('set_nickname', 'Set the nickname of a member', [
        DiscordCommandOption('member', 'Member to update if not yourself', Member, True)
    ], Permissions(change_nickname=True), set_nickname)


    await services.discord.add_slash_command('remote_wos_link', 'Remotely trigger a WOS link', [
        DiscordCommandOption('member', 'Member to link', Member, False),
        DiscordCommandOption('alliance_code', 'Alliance code', str, False),
        DiscordCommandOption('wos_account_id', 'WOS account id', str, False)
    ], Permissions(administrator=True), remote_wos_link)

    await services.discord.add_slash_command('set_all_nicknames', 'Set the nickname of all members', [], Permissions(manage_nicknames=True), set_all_nicknames)

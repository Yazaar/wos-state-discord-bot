from commands.create_age_counter import create_age_counter, get_days_since
from commands.create_alliance_invite import create_alliance_invite
from commands.admin_panel import admin_panel
from commands.nickname_manager import set_all_nicknames, set_nickname
from commands.remote_wos_link import clear_wos_link, remote_wos_link
from commands.verify_account import verify_account, verify_all_users, verify_user
from commands.wos_link_manager import remove_link_selector
from discordHandler import DiscordCommandOption
from services import get_services
from .giftcode_add import giftcode_add
from .find_account import find_account
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

    await services.discord.add_slash_command('remove_link', 'Remove a linked WOS account', [
        DiscordCommandOption('member', 'Member to update if not yourself', Member, True)
    ], Permissions(manage_roles=True), remove_link_selector)

    await services.discord.add_slash_command('set_nickname', 'Set the nickname of a member', [
        DiscordCommandOption('member', 'Member to update if not yourself', Member, True)
    ], Permissions(change_nickname=True), set_nickname)


    await services.discord.add_slash_command('remote_wos_link', 'Remotely trigger a WOS link', [
        DiscordCommandOption('member', 'Member to link', Member, False),
        DiscordCommandOption('alliance_code', 'Alliance code', str, False),
        DiscordCommandOption('wos_account_id', 'WOS account id', str, False),
        DiscordCommandOption('wos_account_name', 'WOS account name', str, False)
    ], Permissions(administrator=True), remote_wos_link)

    await services.discord.add_slash_command('clear_wos_link', 'Clear a WOS account link, to allow another Discord user to claim it', [
        DiscordCommandOption('wos_account_id', 'WOS account id', str, False)
    ], Permissions(moderate_members=True), clear_wos_link)

    await services.discord.add_slash_command('set_all_nicknames', 'Set the nickname of all members', [], Permissions(manage_nicknames=True), set_all_nicknames)

    await services.discord.add_slash_command('verify_user', 'Check if WOS user is in state', [
        DiscordCommandOption('wos_account_id', 'WOS account id to verify', str, False),
        DiscordCommandOption('wos_state_number', 'WOS state number to check if part of', str, False),
    ], Permissions(moderate_members=True), verify_user)

    await services.discord.add_slash_command('verify_account', 'Check if Discord member is in state according to account links', [
        DiscordCommandOption('member', 'Member to verify', Member, False),
        DiscordCommandOption('allowed_state_numbers', 'State numbers to allow (1234,5678,9876) otherwise checking according to alliance whitelists', str, True),
    ], Permissions(moderate_members=True), verify_account)

    await services.discord.add_slash_command('verify_all_users', 'List all current Discord members are still in allowed state', [
    ], Permissions(moderate_members=True), verify_all_users)


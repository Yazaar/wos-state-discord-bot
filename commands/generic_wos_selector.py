from discord.ui import Select, View
from discord import Interaction, Member
from discordHandler import DiscordClient
from services import get_services
from utils.discord_utils import auto_close_interaction_callback

async def generic_wos_selector(
        client: DiscordClient, interaction: Interaction,
        target_param: Member | None, event_id: str, selector_msg: str,
        perm_check):
    guild = interaction.guild
    sender = interaction.user
    target = target_param or interaction.user

    if not guild:
        await interaction.response.send_message('Unable to detect which server the command originates from', ephemeral=True)
        return

    if not isinstance(sender, Member):
        await interaction.response.send_message('Unable to detect which member triggered the command', ephemeral=True)
        return

    if not isinstance(target, Member):
        await interaction.response.send_message('Unable to detect which member to look up', ephemeral=True)
        return

    if not await perm_check(guild, sender, target):
        await interaction.response.send_message('You have no permission to manage the member', ephemeral=True)
        return

    services = get_services()

    guild_id = str(guild.id)
    links = await services.database.get_wos_links(guild_id=guild_id, discord_id=str(target.id), status='active')

    if len(links) == 0:
        await interaction.response.send_message('No linked accounts found', ephemeral=True)
        return

    view = View()
    select = Select(custom_id=event_id)
    select.callback = auto_close_interaction_callback(interaction)

    for link in links:
        select.add_option(label=link.wos_name, value=str(link.id))

    view.add_item(select)
    await interaction.response.send_message(selector_msg, view=view, ephemeral=True)

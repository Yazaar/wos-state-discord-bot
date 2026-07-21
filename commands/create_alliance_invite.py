from discord import Color, Embed, Interaction, Member, TextChannel
from discord.ui import View, Select
from discordHandler import DiscordClient
from services import get_services
from utils.discord_utils import auto_close_interaction_callback

HOURS_24 = 24 * 60 * 60

async def create_alliance_invite(client: DiscordClient, interaction: Interaction):
    member = interaction.user
    if not isinstance(member, Member):
        await interaction.response.send_message('Unable to detect which member triggered the command', ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect the guild which the command originates from', ephemeral=True)
        return

    if not member.guild_permissions.create_instant_invite:
        await interaction.response.send_message('You are not allowed to create invites', ephemeral=True)
        return

    services = get_services()
    guild_id = str(guild.id)

    role_tags = await services.database.get_guild_tags(tag='alliance_role_base', value=[str(i) for i in member.roles], guild_id=guild_id)

    alliance_ids = []
    for i in role_tags:
        if i.space:
            try: alliance_ids.append(int(i.space))
            except Exception: pass

    alliances = await services.database.get_alliances(id_=alliance_ids, guild_id=guild_id)

    if len(alliances) == 0:
        await interaction.response.send_message('You are not in any alliances which you are allowed to create invites for', ephemeral=True)
        return

    view = View()

    alliance_select = Select(custom_id='cai.alliance_select')
    alliance_select.callback = auto_close_interaction_callback(interaction)
    for alliance in alliances:
        alliance_select.add_option(label=f'[{alliance.code}] {alliance.name}', value=str(alliance.id))

    view.add_item(alliance_select)

    await interaction.response.send_message('Select which alliance you would like to create an invite for', view=view, ephemeral=True)

async def create_alliance_invite_selected(client: DiscordClient, interaction: Interaction):
    if not isinstance(interaction.data, dict):
        await interaction.response.send_message('Event data is missing', ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect what server the interaction originates from', ephemeral=True)
        return

    member = interaction.user
    if not isinstance(member, Member):
        await interaction.response.send_message('Unable to detect what member the interaction originates from', ephemeral=True)
        return

    values = interaction.data.get('values', None)
    if not isinstance(values, list) or len(values) < 1:
        await interaction.response.send_message('Event data values is missing', ephemeral=True)
        return

    try: target_alliance_id = int(values[0])
    except Exception:
        await interaction.response.send_message('Provided alliance is of an invalid format', ephemeral=True)
        return

    services = get_services()

    alliance = await services.database.get_alliances(id_=target_alliance_id)
    alliance = alliance[0] if len(alliance) > 0 else None
    if not alliance:
        await interaction.response.send_message('Provided alliance could not be found', ephemeral=True)
        return

    invite_channel = await services.database.get_guild_tags(guild_id=str(guild.id), tag='invite_channel')

    try: invite_channel = guild.get_channel(int(invite_channel[0].value)) if len(invite_channel) > 0 else None
    except Exception: invite_channel = None

    if not isinstance(invite_channel, TextChannel):
        await interaction.response.send_message('Unable to create an invite since the server invite channel is inaccurately bound', ephemeral=True)
        return

    invite = await invite_channel.create_invite(max_uses=1, max_age=HOURS_24)

    await services.database.create_join_invite(target_alliance_id, invite.code, str(member.id))

    embed = Embed(title='Invite details', color=Color.green())
    embed.add_field(name='Alliance', value=f'[{alliance.code}] {alliance.name}', inline=False)
    embed.add_field(name='Link', value=invite.url, inline=True)
    embed.add_field(name='Code', value=invite.code, inline=True)

    await interaction.response.send_message(
        f'An invite has been created for *[{alliance.code}] {alliance.name}*\n\n' +
        '> Provide the invited user the following link and code. Once they join ' +
        'via the link, provide the code via the alliance authentication system for instant access to the alliance.', embed=embed, ephemeral=True)

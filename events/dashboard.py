from discord import ChannelType, HTTPException, InvalidData, Member, Message, Interaction, ButtonStyle, MessageType, NotFound, TextChannel, Thread
from discord.ui import Button, View, Select
from utils.discord_utils import auto_close_interaction_callback
from discordHandler import DiscordClient
from services import get_services
import re, asyncio, datetime

async def release_selected_tnc_draft(client: DiscordClient, interaction: Interaction, confirmed_channel: str | None = None):
    member = interaction.user
    if not isinstance(member, Member):
        await interaction.response.send_message('Unable to detect what member of the server triggered this interaction', ephemeral=True)
        return

    if confirmed_channel:
        channel_id = confirmed_channel
    else:
        values = interaction.data.get('values', None) if interaction.data else None
        if not isinstance(values, list) or len(values) == 0:
            await interaction.response.send_message('Selection not found', ephemeral=True)
            return
        channel_id = values[0]

    if not isinstance(channel_id, str):
        await interaction.response.send_message('Invalid selection', ephemeral=True)
        return

    if not interaction.guild:
        await interaction.response.send_message('Unable to recognize server', ephemeral=True)
        return

    try:
        channel_id_int = int(channel_id)
    except Exception:
        await interaction.response.send_message('Invalid selection format', ephemeral=True)
        return

    try:
        channel = await interaction.guild.fetch_channel(channel_id_int)
        if not isinstance(channel, Thread):
            await interaction.response.send_message('Selection is not of type thread', ephemeral=True)
            return
    except InvalidData:
        await interaction.response.send_message('Terms and conditions thread not found', ephemeral=True)
        return
    except NotFound:
        await interaction.response.send_message('Terms and conditions thread not found', ephemeral=True)
        return
    except HTTPException:
        await interaction.response.send_message('Failed to receive the terms and conditions thread, feel free to try again', ephemeral=True)
        return

    if not confirmed_channel:
        confirm_tnc_release = Button(label='Confirm', style=ButtonStyle.green, custom_id=f'confirm_tnc_release::{channel.id}')
        confirm_tnc_release.callback = auto_close_interaction_callback(interaction)

        view = View()
        view.add_item(confirm_tnc_release)

        await interaction.response.send_message(f'Confirm the release of the following terms and conditions: {channel.mention}', view=view, ephemeral=True)
        return

    services = get_services()
    target_channel_id_raw = await services.database.get_guild_tags(guild_id=str(interaction.guild.id), tag='tnc_channel', limit=1)

    try:
        target_channel_id = int(target_channel_id_raw[0].value) if len(target_channel_id_raw) > 0 and target_channel_id_raw[0].value else None
    except Exception:
        target_channel_id = None

    if not isinstance(target_channel_id, int):
        await interaction.response.send_message(
            'Unable to detect the target text channel for terms and conditions, is it linked?', ephemeral=True)
        return

    target_channel = channel.guild.get_channel(target_channel_id)
    if not isinstance(target_channel, TextChannel):
        await interaction.response.send_message(
            'Terms and conditions text channel was unable to be found, is it properly linked to a text channel?\n', ephemeral=True)
        return

    target_ch_perms = target_channel.permissions_for(member)
    if not target_ch_perms.manage_channels or not target_ch_perms.manage_messages:
        await interaction.response.send_message(
            'You are no allowed to complete this operation due to missing permission at the' +
            'target terms and conditions channel (required: manage channel, manage messages)', ephemeral=True
        )
        return

    last_message = [i async for i in channel.history(limit=1)]

    if len(last_message) == 0:
        await interaction.response.send_message(f'No messages found in {channel.mention}', ephemeral=True)
        return

    last_message = last_message[0]

    await interaction.response.send_message(f'The release of terms and conditions {channel.mention} is being processed...', ephemeral=True)

    bot_user = client.get_self_user()

    create_mode = False
    target_prev_ref: Message | None = None

    view = View()
    alliance_request = Button(label='💬 Alliance join request', custom_id='tnc.alliance_join_req')
    join_by_code = Button(label='📜 Join by invite code', custom_id='tnc.code_join')
    view.add_item(alliance_request)
    view.add_item(join_by_code)

    try:
        async for message in channel.history(limit=None, oldest_first=True):
            if message.type != MessageType.default: continue
            is_last_message = message.id == last_message.id
            if not create_mode:
                while True:
                    matches = [i async for i in target_channel.history(limit=1, oldest_first=True, after=target_prev_ref)]
                    if len(matches) == 0:
                        create_mode = True
                    else:
                        next_message = matches[0]
                        if next_message.author.id != bot_user.id:
                            await next_message.delete()
                            continue
                        await next_message.edit(content=message.content, view=view if is_last_message else None)
                        await next_message.clear_reactions()
                        target_prev_ref = next_message
                    break

            if create_mode:
                if is_last_message: target_prev_ref = await target_channel.send(content=message.content, view=view)
                else: await target_channel.send(content=message.content)

            if last_message.id == message.id: break
    except Exception as e:
        print(e)


    async for message in target_channel.history(limit=None, oldest_first=True, after=target_prev_ref):
        await message.delete()

    try: await interaction.edit_original_response(content=f'The release of terms and conditions {channel.mention} is complete')
    except Exception: pass

async def activate_tnc_draft_selector(client: DiscordClient, interaction: Interaction):
    channel = interaction.channel
    if not isinstance(channel, TextChannel):
        await interaction.response.send_message('Have to do this interaction via a regular text channel', ephemeral=True)
        return

    member = interaction.user
    if not isinstance(member, Member):
        await interaction.response.send_message('Unable to detect what member triggered the interaction', ephemeral=True)
        return

    if not member.guild_permissions.manage_channels:
        await interaction.response.send_message('Unable to detect what member triggered the interaction', ephemeral=True)
        return

    pattern = r'^termsV\d+$'
    draft_threads = [thread for thread in channel.threads if re.match(pattern, thread.name)]

    async for thread in channel.archived_threads():
        if re.match(pattern, thread.name):
            draft_threads.append(thread)

    if len(draft_threads) == 0:
        await interaction.response.send_message('No terms and condition drafts found.\n' +
            '*Tip: try to manually search through archived threads and un-archive the one you are after and then try again*', ephemeral=True)
        return

    select = Select(custom_id='release-terms-thread')
    select.callback = auto_close_interaction_callback(interaction)
    for thread in draft_threads:
        select.add_option(label=thread.name, value=str(thread.id))

    view = View()
    view.add_item(select)


    await interaction.response.send_message('Select the terms and conditions version you would like to publish', view=view, ephemeral=True)

async def create_tnc_draft(client: DiscordClient, interaction: Interaction):
    channel = interaction.channel

    if not isinstance(channel, TextChannel):
        await interaction.response.send_message('Have to do this interaction via a regular text channel', ephemeral=True)
        return


    member = interaction.user
    if not isinstance(member, Member):
        await interaction.response.send_message('Unable to detect what member triggered the interaction', ephemeral=True)
        return

    channel_perms = channel.permissions_for(member)
    if not channel_perms.create_public_threads:
        await interaction.response.send_message(
            'You are not allowed to create terms and condition drafts due to missing create public threads permission',
            ephemeral=True
        )
        return

    services = get_services()

    version = await services.database.get_next_tnc_version()
    if not version:
        await interaction.response.send_message('Unable to detect terms and conditions versioning', ephemeral=True)
        return

    thread_name = f'termsV{version}'
    for thread in channel.threads:
        if thread.name == thread_name:
            await thread.delete()

    current_time = datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(seconds=-30)
    text_thread = await channel.create_thread(name=thread_name, type=ChannelType.public_thread)

    bot_user = client.get_self_user()
    for i in range(4):
        deleted = False
        async for message in channel.history(after=current_time):
            if message.author.id == bot_user.id and thread_name == message.content:
                deleted = True
                try: await message.delete()
                except Exception: pass
                break
        if deleted: break
        if i != 3: await asyncio.sleep(1)

    await interaction.response.send_message(f'Terms and conditions draft created: {text_thread.mention}', ephemeral=True)    

import datetime, time
from discord import Interaction, Member, TextChannel, Embed
from discord.ui import Button, View
from discordHandler import DiscordClient

def get_date_info(dt: datetime.datetime):
    dt = dt.replace(tzinfo=datetime.timezone.utc)

    birthdate_date = dt.strftime('%Y-%m-%d')
    birthdate_epoch = int(dt.timestamp())
    days_age = int(time.time() - birthdate_epoch) // 86400

    today = datetime.datetime.now(datetime.timezone.utc)

    sign = 1
    if dt > today:
        sign = -1
        today, dt = dt, today

    years = today.year - dt.year
    months = today.month - dt.month
    days = today.day - dt.day

    if days < 0:
        months -= 1
        prev_month = today.replace(day=1) - datetime.timedelta(days=1)
        days += prev_month.day

    if months < 0:
        years -= 1
        months += 12

    diff_details = (years * sign, months * sign, days * sign)

    return birthdate_date, birthdate_epoch, days_age, diff_details

def create_counter_embed(dt: datetime.datetime, title: str | None, description: str | None):
    date_str, date_epoch, days_age, detailed_diff = get_date_info(dt)
    years, months, days = detailed_diff

    now = datetime.datetime.now(datetime.timezone.utc)
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')

    embed = Embed(title=title, description=description)
    embed.add_field(name='date', value=date_str, inline=True)
    embed.add_field(name='days', value=str(days_age), inline=True)
    embed.add_field(name='Detailed age', value=f'{years} years, {months} months, {days} days', inline=False)
    embed.set_footer(text=f'Last updated {now_str} UTC')
    return embed

async def get_days_since(client: DiscordClient, interaction: Interaction, target_date: str, public: str):
    try: dt = datetime.datetime.strptime(target_date, '%Y-%m-%d')
    except Exception:
        await interaction.response.send_message('Failed to parse date, ensure format YYYY-MM-DD', ephemeral=True)
        return

    date_str, date_epoch, days_age, detailed_diff = get_date_info(dt)
    years, months, days = detailed_diff

    if days_age > 0:
        await interaction.response.send_message(
            f'The date {date_str} was {days_age} days ago ({years} years, {months} months, {days} days)', ephemeral=public != '1'
        )
    else:
        await interaction.response.send_message(
            f'The date {date_str} is in {-days_age} days ({-years} years, {-months} months, {-days} days)', ephemeral=public != '1'
        )

async def create_age_counter(
        client: DiscordClient, interaction: Interaction, target_date: str,
        target_message: str | None, target_channel: TextChannel | None,
        title: str | None, description: str | None):
    guild = interaction.guild
    member = interaction.user

    channel = target_channel or interaction.channel

    if target_message:
        try: target_msg_id = int(target_message)
        except Exception:
            await interaction.response.send_message('The provided target message is of an invalid format', ephemeral=True)
            return
    else: target_msg_id = None

    if not guild:
        await interaction.response.send_message('Unable to detect which server this interaction originates from', ephemeral=True)
        return

    if not isinstance(channel, TextChannel):
        await interaction.response.send_message('Unable to detect the target text channel', ephemeral=True)
        return

    if not isinstance(member, Member):
        await interaction.response.send_message('Unable to detect which text cahnnel this interaction originates from', ephemeral=True)
        return

    perms = channel.permissions_for(member)

    if not perms.manage_channels or not perms.manage_messages or not member.guild_permissions.manage_channels or not member.guild_permissions.manage_messages:
        await interaction.response.send_message('You do not have permission to create an age counter for this server and text channel', ephemeral=True)
        return

    try: dt = datetime.datetime.strptime(target_date, '%Y-%m-%d')
    except Exception:
        await interaction.response.send_message('Failed to process the timestamp, make sure it is in the format YYYY-MM-DD', ephemeral=True)
        return

    msg_embed = create_counter_embed(dt, title, description)
    view = View()
    refresh_btn = Button(label='🔃 Refresh', custom_id=f'age_counter.refresh::{int(dt.timestamp())}')
    view.add_item(refresh_btn)

    if target_msg_id:
        try: target_msg_ref = await channel.fetch_message(target_msg_id)
        except Exception:
            await interaction.response.send_message('Unable to find the referenced target message', ephemeral=True)
            return

        try:
            await target_msg_ref.edit(embed=msg_embed, view=view)
        except Exception:
            await interaction.response.send_message('Failed to edit the target message', ephemeral=True)
            return        
    else:
        try: await channel.send(None, embed=msg_embed, view=view)
        except Exception:
            await interaction.response.send_message(f'Failed to create age counter in channel {channel.mention}', ephemeral=True)
            return

    await interaction.response.send_message('Age counter created', ephemeral=True, delete_after=5)

async def refresh_age_counter(client: DiscordClient, interaction: Interaction, target_date: str):
    if not interaction.message:
        await interaction.response.send_message('Unable to find the interacted message', ephemeral=True)
        return

    try: dt = datetime.datetime.fromtimestamp(int(target_date), tz=datetime.timezone.utc)
    except Exception:
        await interaction.response.send_message('Failed to detect the timestamp', ephemeral=True)
        return

    title = None
    description = None

    prev_embed = interaction.message.embeds[0] if interaction.message.embeds and len(interaction.message.embeds) > 0 else None
    if prev_embed:
        title = prev_embed.title
        description = prev_embed.description

    embed = create_counter_embed(dt, title, description)

    await interaction.message.edit(embed=embed)
    await interaction.response.send_message('Date counter refreshed!', silent=True, delete_after=5, ephemeral=True)

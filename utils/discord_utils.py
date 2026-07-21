from discord import ChannelType, Color, Embed, Guild, Interaction, Member, Role
import typing

from database.db_shared import DatabaseInterface
if typing.TYPE_CHECKING:
    from discord.guild import GuildChannel

def auto_close_interaction_callback(interaction_to_delete: Interaction):
    async def on_callback(interaction: Interaction):
        await interaction_to_delete.delete_original_response()
    return on_callback

def component_array_to_dict(data: list):
    processed: dict[str, str] = {}

    for item in data:
        if not isinstance(item, dict): continue
        sub_components = item.get('components', None)
        if not isinstance(sub_components, list): continue

        for value_pairs in sub_components:
            if not isinstance(value_pairs, dict): continue

            value = value_pairs.get('value')
            key = value_pairs.get('custom_id')

            if not isinstance(key, str) or not isinstance(value, str):
                continue

            processed[key] = value

    return processed

def find_category_by_name(category_name: str, channels: typing.Sequence['GuildChannel']):
    for channel in channels:
        if channel.type == ChannelType.category and channel.name == category_name:
            return channel

def find_text_channel_by_name(channel_name: str, channels: typing.Sequence['GuildChannel']):
    for channel in channels:
        if channel.type == ChannelType.text and channel.name == channel_name:
            return channel

def find_voice_channel_by_name(channel_name: str, channels: typing.Sequence['GuildChannel']):
    for channel in channels:
        if channel.type == ChannelType.voice and channel.name == channel_name:
            return channel

def find_role_by_name(role_name: str, roles: typing.Sequence[Role]):
    for role in roles:
        if role.name == role_name:
            return role

def updated_embed(embeds: list[Embed], *, color: int | Color | None | None = None):
    updated_embeds: list[Embed] = []
    for embed in embeds:
        next_embed = Embed(color=embed.color if color is None else color, title=embed.title)
        for field in embed.fields: next_embed.add_field(name=field.name, value=field.value, inline=field.inline)
        if embed.thumbnail and embed.thumbnail.url: next_embed.set_thumbnail(url=embed.thumbnail.url)
        updated_embeds.append(next_embed)
    return updated_embeds

async def has_permission(permission: str, guild: Guild, member: Member, database: DatabaseInterface):
    guild_id = str(guild.id)

    values: list[str] = []

    for role in member.roles:
        values.append(f'R:{role.id}')
    values.append(f'M:{member.id}')

    results = await database.get_guild_tags(guild_id=guild_id, tag=f'perm.{permission}', value=values, limit=1)
    return len(results) > 0

from discord import Color, Embed, Interaction, Member
from discordHandler import DiscordClient
from services import get_services
from utils.wos_api_utils import WosPlayer, get_player
from utils.memory_cache import MemoryCache

wos_acc_cache = MemoryCache(300)

async def search_wos_account(client: DiscordClient, interaction: Interaction, wos_id: str, public: str | None):
    try: wos_id_num = int(wos_id)
    except Exception:
        await interaction.response.send_message('Invalid WOS account ID', ephemeral=public != '1')
        return

    player = wos_acc_cache.get(wos_id)

    try:
        if not isinstance(player, WosPlayer): player = await get_player(wos_id_num)
        if not isinstance(player, WosPlayer): raise Exception('WOS account not found')
    except Exception:
        await interaction.response.send_message('WOS account not found', ephemeral=public != '1')
        return

    wos_acc_cache.set(wos_id, player)

    wos_acc_embed = Embed(title='WOS account')
    wos_acc_embed.add_field(name='Name', value=player.name, inline=False)
    wos_acc_embed.add_field(name='Furnace', value=player.stove_lvl, inline=False)
    wos_acc_embed.add_field(name='State', value=player.server, inline=False)
    if player.avatar_img: wos_acc_embed.set_thumbnail(url=player.avatar_img)

    await interaction.response.send_message('WOS account found', embed=wos_acc_embed, ephemeral=public != '1')

async def find_account(client: DiscordClient, interaction: Interaction, discord: Member | None, wos_id: str | None, wos_name: str | None, public: str | None):
    services = get_services()

    if not discord and not wos_id and not wos_name:
        await interaction.response.send_message('No search parameters provided', ephemeral=True)
        return

    guild = interaction.guild
    if not guild:
        await interaction.response.send_message('Unable to detect what server the command was triggered from', ephemeral=True)
        return

    guild_id = str(guild.id)

    links = await services.database.get_wos_links(
        guild_id=guild_id,
        discord_id=str(discord.id) if discord else None,
        wos_id=wos_id, wos_name=wos_name,
        mode=['guild-search', 'wos-name-nocase']
    )

    wos_accs: dict[str, WosPlayer] = {}

    embeds = []

    for lnk in links:
        try:
            lnk_discord_member = guild.get_member(int(lnk.discord_id))
            if not lnk_discord_member: raise Exception('Not found')
            lnk_discord_member = (lnk_discord_member.display_name, lnk_discord_member.avatar.url if lnk_discord_member.avatar else None)
        except Exception:
            lnk_discord_member = (lnk.discord_id, None)

        try:
            lnk_wos_acc = wos_accs.get(lnk.wos_id, None) or await get_player(int(lnk.wos_id))
            if not lnk_wos_acc: raise Exception('Not found')
            wos_accs[lnk.wos_id] = lnk_wos_acc
            lnk_wos_acc = (lnk_wos_acc.name, lnk_wos_acc.avatar_img, lnk_wos_acc.player_id, lnk_wos_acc.server, lnk_wos_acc.stove_lvl)
        except Exception:
            lnk_wos_acc = (lnk.wos_id, None, lnk.wos_id, None, None)

        linked_acc_embed = Embed(title='Linked account', color=Color.gold())
        linked_acc_embed.add_field(name='Discord', value=lnk_discord_member[0], inline=False)
        linked_acc_embed.add_field(name='WOS', value=lnk_wos_acc[0], inline=False)
        linked_acc_embed.add_field(name='WOS (id)', value=lnk_wos_acc[2], inline=True)
        if lnk_wos_acc[3]: linked_acc_embed.add_field(name='WOS (state)', value=lnk_wos_acc[3], inline=True)
        if lnk_wos_acc[4]: linked_acc_embed.add_field(name='WOS (furnace)', value=lnk_wos_acc[4], inline=True)
        if lnk_wos_acc[1]: linked_acc_embed.set_thumbnail(url=lnk_wos_acc[1])
        elif lnk_discord_member[1]: linked_acc_embed.set_thumbnail(url=lnk_discord_member[1])
        embeds.append(linked_acc_embed)

    if len(embeds) == 0:
        embeds.append(Embed(title='No links found', description='Found no linked accounts with the provided parameters'))

    await interaction.response.send_message('Found the following accounts according to your query', embeds=embeds, ephemeral=public != '1')

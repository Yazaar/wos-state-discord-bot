from discord import Color, Embed, Interaction, Member
from discordHandler import DiscordClient
from services import get_services
from utils.memory_cache import MemoryCache

wos_acc_cache = MemoryCache(300)

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

    embeds = []

    for lnk in links:
        try:
            lnk_discord_member = guild.get_member(int(lnk.discord_id))
            if not lnk_discord_member: raise Exception('Not found')
            lnk_discord_member = (lnk_discord_member.display_name, lnk_discord_member.avatar.url if lnk_discord_member.avatar else None)
        except Exception:
            lnk_discord_member = (lnk.discord_id, None)

        alliance = None

        if lnk.alliance_id:
            alliance = await services.database.get_alliances(id_=lnk.alliance_id, limit=1)
            alliance = alliance[0] if len(alliance) == 1 else None

        linked_acc_embed = Embed(title='Linked account', color=Color.gold())
        linked_acc_embed.add_field(name='Discord', value=lnk_discord_member[0], inline=False)
        linked_acc_embed.add_field(name='WOS', value=lnk.wos_name, inline=False)
        linked_acc_embed.add_field(name='WOS (id)', value=lnk.wos_id, inline=True)
        if alliance: linked_acc_embed.add_field(name='WOS (state)', value=alliance.state, inline=True)
        if lnk_discord_member[1]: linked_acc_embed.set_thumbnail(url=lnk_discord_member[1])
        embeds.append(linked_acc_embed)

    if len(embeds) == 0:
        embeds.append(Embed(title='No links found', description='Found no linked accounts with the provided parameters'))

    await interaction.response.send_message('Found the following accounts according to your query', embeds=embeds, ephemeral=public != '1')

class WosLink:
    def __init__(self,
                 id_: int, timestamp: int, guild_id: str, alliance_id: int | None,
                 discord_id: str, wos_id: str, wos_name: str, status: str):
        self.id = id_
        self.timestamp = timestamp
        self.guild_id = guild_id
        self.discord_id = discord_id
        self.alliance_id = alliance_id
        self.wos_id = wos_id
        self.wos_name = wos_name
        self.status = status

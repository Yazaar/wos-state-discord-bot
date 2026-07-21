class GuildTag:
    def __init__(self, id_: int, tag: str, guild_id: str, value: str, space: str | None):
        self.id = id_
        self.tag = tag
        self.guild_id = guild_id
        self.value = value
        self.space = space

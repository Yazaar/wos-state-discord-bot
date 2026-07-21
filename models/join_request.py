class JoinRequest:
    def __init__(self, id_: int, timestamp: int,
                 discord_id: str, discord_username: str, discord_nickname: str,
                 wos_id: str, wos_username: str, wos_alliance_id: int,
                 discord_message_id: str | None = None, status: str = 'pending', handler_discord_id: str | None = None):
        self.id = id_
        self.timestamp = timestamp
        self.discord_id = discord_id
        self.discord_username = discord_username
        self.discord_nickname = discord_nickname
        self.wos_id = wos_id
        self.wos_username = wos_username
        self.wos_alliance_id = wos_alliance_id
        self.discord_message_id = discord_message_id
        self.status = status
        self.handler_discord_id = handler_discord_id

class JoinInvite:
    def __init__(self, id_: int, invite_code: str, timestamp: int, wos_alliance_id: int, creator_discord_id: str, executed: bool):
        self.id = id_
        self.invite_code = invite_code
        self.timestamp = timestamp
        self.wos_alliance_id = wos_alliance_id
        self.creator_discord_id = creator_discord_id
        self.executed = executed

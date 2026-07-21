class Giftcode:
    def __init__(self, id_: int, code: str, active_date: int, expiry_date: int | None, close_date: int | None):
        self.id = id_
        self.code = code
        self.active_date = active_date
        self.expiry_date = expiry_date
        self.close_date = close_date

class GiftcodeMessage:
    def __init__(self, id_: int, giftcode_id: int, guild_id: str, channel_id: str, message_id: str):
        self.id = id_
        self.giftcode_id = giftcode_id
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.message_id = message_id

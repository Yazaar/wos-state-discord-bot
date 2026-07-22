from abc import ABC, abstractmethod

from models.alliance import Alliance
from models.giftcode import Giftcode, GiftcodeMessage
from models.guild_tag import GuildTag
from models.join_request import JoinInvite, JoinRequest
from models.wos_link import WosLink

class UnsetField: pass

UNSET = UnsetField()

class DB_NOT_INSTALLED_ERROR(Exception): pass

class DB_NO_CONFIG_ERROR(Exception): pass

class DB_CONNECT_ERROR(Exception): pass

class DatabaseInterface(ABC):
    @abstractmethod
    async def startup(self):
        pass

    @abstractmethod
    async def get_next_tnc_version(self) -> int:
        pass

    @abstractmethod
    async def add_unique_guild_tag(self, guild_id: str, value: str, tag: str) -> None:
        pass

    @abstractmethod
    async def add_guild_tag(
            self,
            guild_id: str,
            value: str,
            tag: str, *,
            space: str | None = None) -> GuildTag:
        pass

    @abstractmethod
    async def remove_guild_tag(self, guild_tag: GuildTag) -> None:
        pass

    @abstractmethod
    async def get_guild_tags(
            self,
            id_: int | None = None, tag: str | None = None,
            guild_id: str | None = None, value: str | list[str] | None = None,
            space: str | None = None, limit: int | None = None) -> list[GuildTag]:
        pass

    @abstractmethod
    async def update_guild_tag(
            self, guild_tag: GuildTag, value: str | None = None, space: str | None = None) -> GuildTag:
        pass

    @abstractmethod
    async def get_giftcodes_by_code(self, codes: list[str]) -> list[Giftcode]:
        pass

    @abstractmethod
    async def get_active_giftcodes(self) -> list[Giftcode]:
        pass

    @abstractmethod
    async def register_giftcode(self, code: str, active_date: int, expiry_date: int | None = None) -> Giftcode:
        pass

    @abstractmethod
    async def update_giftcode(
            self, giftcode: Giftcode, code: str | None = None, active_date: int | None = None,
            expiry_date: int | None | UnsetField = UNSET, close_date: int | None | UnsetField = UNSET) -> Giftcode:
        pass

    @abstractmethod
    async def register_giftcode_message(self, giftcode_id: int, guild_id: str, channel_id: str, message_id: str) -> GiftcodeMessage:
        pass

    @abstractmethod
    async def get_giftcode_messages(
        self, id_: int | None = None, giftcode_id: int | None = None, guild_id: str | None = None,
        channel_id: str | None = None, message_id: str | None = None, limit: int | None = None) -> list[GiftcodeMessage]:
        pass

    @abstractmethod
    async def add_alliance(self, code: str, name: str, state: int, guild_id: str) -> Alliance:
        pass

    @abstractmethod
    async def get_alliances(
            self,
            id_: int | list[int] | None = None, code: str | None = None, name: str | None = None, state: int | None = None, guild_id: str | None = None,
            limit: int | None = None) -> list[Alliance]:
        pass

    @abstractmethod
    async def remove_alliance(self, alliance: Alliance) -> None:
        pass

    @abstractmethod
    async def register_join_request(self, discord_id: str, discord_username: str, discord_nickname: str, wos_id: str, wos_username: str, wos_alliance_id: int) -> JoinRequest:
        pass

    @abstractmethod
    async def update_join_request(self, join_request: JoinRequest,
            discord_message_id: str | None = None, status: str | None = None, handler_discord_id: str | None = None ) -> JoinRequest:
        pass

    @abstractmethod
    async def find_latest_join_request(self, discord_id: str, wos_id: str, wos_alliance_id: int) -> JoinRequest | None:
        pass

    @abstractmethod
    async def get_join_requests(self, id_: str | None = None, limit: int | None = None) -> list[JoinRequest]:
        pass

    @abstractmethod
    async def whitelist_state_add(self, guild_id: str, wos_state: str) -> None:
        pass

    @abstractmethod
    async def whitelist_state_remove(self, guild_id: str, wos_state: str) -> None:
        pass

    @abstractmethod
    async def whitelist_state_list(self, guild_id: str) -> list[str]:
        pass

    @abstractmethod
    async def update_join_invite(self, join_invite: JoinInvite, executed: bool | None = None) -> JoinInvite:
        pass

    @abstractmethod
    async def create_join_invite(self, alliance_id: int, invite_code: str, creator_discord_id: str) -> JoinInvite:
        pass

    @abstractmethod
    async def get_join_invite(
            self,
            id_: int | None = None,
            timestamp: int | None = None,
            invite_code: str | None = None,
            wos_alliance_id: int | None = None,
            creator_discord_id: str | None = None,
            executed: bool | None = None,
            limit: int | None = None) -> list[JoinInvite]:
        pass

    @abstractmethod
    async def get_wos_links(
            self,
            id_: int | None = None, guild_id: str | None = None, alliance_id: int | None = None, discord_id: str | None = None, wos_id: str | None = None,
            status: str | None = None, limit: int | None = None, wos_name: str | None = None, mode: list[str] = []) -> list[WosLink]:
        pass

    @abstractmethod
    async def register_wos_link(self, guild_id: str, alliance_id: int | None, discord_id: str, wos_id: str, wos_name: str) -> WosLink:
        pass

    @abstractmethod
    async def update_wos_link(
        self, wos_link: WosLink, timestamp: int | None = None,
        guild_id: str | None = None, alliance_id: int | None = None, discord_id: str | None = None,
        wos_id: str | None = None, wos_name: str | None = None,
        status: str | None = None) -> WosLink:
        pass

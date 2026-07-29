import sqlite3, time

from models.alliance import Alliance
from models.guild_tag import GuildTag
from models.join_request import JoinInvite, JoinRequest
from models.wos_link import WosLink
from .db_shared import DatabaseInterface, UnsetField, UNSET
from models.giftcode import Giftcode, GiftcodeMessage

class EmptyFieldException(Exception): pass

def auto_field(value, values: list):
    if value is None:
        return 'IS NULL'
    elif isinstance(value, list):
        if not value: raise EmptyFieldException()
        values.extend(value)
        placeholders = ','.join('?' for _ in value)
        return f'IN ({placeholders})'
    else:
        values.append(value)
        return '= ?'

class Sqlite3DB(DatabaseInterface):
    def __init__(self):
        self.__con = sqlite3.connect('sqlite3.db')

    async def startup(self):
        await self.__create_database()

    async def __create_database(self):
        c = None
        try:
            c = self.__con.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS sequences (
                    id TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
            ''')
            c.execute('INSERT OR IGNORE INTO sequences (id, value) VALUES (\'tnc_version\', 0)')
            c.execute('''
                CREATE TABLE IF NOT EXISTS giftcodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL,
                    activeDate INTEGER NOT NULL,
                    expiryDate INTEGER,
                    closeDate INTEGER
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS giftcode_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giftcodeId INTEGER NOT NULL,
                    guildId TEXT NOT NULL,
                    channelId TEXT NOT NULL,
                    messageId TEXT NOT NULL,
                    FOREIGN KEY (giftcodeId) REFERENCES giftcodes(id)
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS guild_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guildId TEXT NOT NULL,
                    value TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    space TEXT
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS alliances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guildId TEXT NOT NULL,
                    code TEXT NOT NULL,
                    name TEXT NOT NULL,
                    state INTEGER NOT NULL
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS join_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    discordId TEXT NOT NULL,
                    discordUsername TEXT NOT NULL,
                    discordNickname TEXT NOT NULL,
                    wosId TEXT NOT NULL,
                    wosUsername TEXT NOT NULL,
                    wosAllianceId INTEGER NOT NULL,
                    discordMessageId TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    handlerDiscordId TEXT
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS join_invites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    inviteCode TEXT NOT NULL,
                    wosAllianceId INTEGER NOT NULL,
                    creatorDiscordId TEXT NOT NULL,
                    executed INTEGER NOT NULL DEFAULT 0
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS wos_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    discordId TEXT NOT NULL,
                    wosId TEXT NOT NULL,
                    wosName TEXT,
                    guildId TEXT NOT NULL,
                    allianceId INTEGER,
                    status TEXT NOT NULL DEFAULT 'active'
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS wos_state_whitelist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guildId TEXT NOT NULL,
                    wosState TEXT NOT NULL
                )
            ''')
            self.__con.commit()
        finally:
            if c: c.close()

    async def get_next_tnc_version(self) -> int:
        c = None
        try:
            c = self.__con.cursor()
            c.execute('UPDATE sequences SET value = value + 1 WHERE id = \'tnc_version\' RETURNING value')
            row = c.fetchone()
            if not row: raise Exception('Unable to detect registered sequence')
            self.__con.commit()
            return row[0]
        finally:
            if c: c.close()

    async def add_unique_guild_tag(self, guild_id: str, value: str, tag: str) -> None:
        c = None
        try:
            c = self.__con.cursor()
            c.execute('SELECT id, value FROM guild_tags WHERE guildId = ? AND tag = ? LIMIT 1', (guild_id, tag))
            entry = c.fetchone()
            if entry:
                if entry[1] == value: return
                c.execute('UPDATE guild_tags set value = ? WHERE id = ?', (value, entry[0]))
            else:
                c.execute('INSERT INTO guild_tags(guildId, value, tag) VALUES(?, ?, ?)', (guild_id, value, tag))
            self.__con.commit()
        finally:
            if c: c.close()

    async def add_guild_tag(
            self,
            guild_id: str,
            value: str,
            tag: str, *,
            space: str | None = None) -> GuildTag:
        c = None
        try:
            c = self.__con.cursor()
            keys = ['guildId', 'tag', 'value']
            values = [guild_id, tag, value]
            if space:
                keys.append('space')
                values.append(space)

            keys_sect = ', '.join(keys)
            values_sect = ','.join(['?'] * len(values))
            c.execute(f'INSERT INTO guild_tags({keys_sect}) VALUES({values_sect}) RETURNING id', values)
            row = c.fetchone()
            self.__con.commit()
            if not row: raise Exception('Unable to detect registered guild tag')
            return GuildTag(row[0], tag, guild_id, value, space)
        finally:
            if c: c.close()

    async def update_guild_tag(
            self, guild_tag: GuildTag, value: str | None = None, space: str | None = None) -> GuildTag:
        c = None
        try:
            fields = []
            values = []
            if value:
                fields.append('value = ?')
                values.append(value)
                guild_tag.value = value
            if space:
                fields.append('space = ?')
                values.append(space)
                guild_tag.space = space

            if len(values) > 0:
                values.append(guild_tag.id)
                c = self.__con.cursor()
                field_str = ', '.join(fields)
                c.execute(f'UPDATE guild_tags SET {field_str} WHERE id = ?', values)
                self.__con.commit()

            return guild_tag
        finally:
            if c: c.close()

    async def remove_guild_tag(self, guild_tag: GuildTag) -> None:
        c = None
        try:
            c = self.__con.cursor()
            c.execute('DELETE FROM guild_tags WHERE id = ?', (guild_tag.id,))
            self.__con.commit()
        finally:
            if c: c.close()

    async def get_guild_tags(
            self,
            id_: int | None = None, tag: str | None = None,
            guild_id: str | None = None, value: str | list[str] | None = None,
            space: str | None = None, limit: int | None = None) -> list[GuildTag]:
        c = None
        try:
            c = self.__con.cursor()
            where_clauses = []
            values = []
            if id_:
                where_clauses.append('id = ?')
                values.append(id_)
            if tag:
                where_clauses.append('tag = ?')
                values.append(tag)
            if guild_id:
                where_clauses.append('guildId = ?')
                values.append(guild_id)
            if value:
                try: where_clauses.append(f'value {auto_field(value, values)}')
                except EmptyFieldException: return []
            if space:
                where_clauses.append('space = ?')
                values.append(space)

            where_query = ''
            if len(where_clauses) > 0: where_query = ' WHERE ' + ' AND '.join(where_clauses)

            limit_query = ''
            if limit and limit > 0:
                limit_query = ' LIMIT ?'
                values.append(limit)
            c.execute(f'SELECT id, tag, guildId, value, space FROM guild_tags{where_query}{limit_query}', values)
            rows = c.fetchall()
            if not rows: return []
            return [GuildTag(row[0], row[1], row[2], row[3], row[4]) for row in rows]
        finally:
            if c: c.close()

    async def get_wos_links(
            self,
            id_: int | None = None, guild_id: str | None = None, alliance_id: int | None = None, discord_id: str | None = None, wos_id: str | None = None,
            status: str | list[str] | None = None, limit: int | None = None, wos_name: str | None = None, mode: list[str] = []) -> list[WosLink]:
        c = None
        try:
            c = self.__con.cursor()

            all_values = []
            any_values = []
            where_all_clauses = []
            where_any_clauses = []

            guild_search = mode and 'guild-search' in mode

            if id_:
                if guild_search:
                    any_values.append(id_)
                    where_any_clauses.append('id = ?')
                else:
                    all_values.append(id_)
                    where_all_clauses.append('id = ?')
            if guild_id:
                all_values.append(guild_id)
                where_all_clauses.append('guildId = ?')
            if alliance_id:
                if guild_search:
                    any_values.append(alliance_id)
                    where_any_clauses.append('allianceId = ?')
                else:
                    all_values.append(discord_id)
                    where_all_clauses.append('discordId = ?')
            if discord_id:
                if guild_search:
                    any_values.append(discord_id)
                    where_any_clauses.append('discordId = ?')
                else:
                    all_values.append(discord_id)
                    where_all_clauses.append('discordId = ?')
            if wos_id:
                if guild_search:
                    any_values.append(wos_id)
                    where_any_clauses.append('wosId = ?')
                else:
                    all_values.append(wos_id)
                    where_all_clauses.append('wosId = ?')
            if status:
                if guild_search:
                    try: where_any_clauses.append(f'status {auto_field(status, any_values)}')
                    except EmptyFieldException: return []
                else:
                    try: where_all_clauses.append(f'status {auto_field(status, all_values)}')
                    except EmptyFieldException: return []
            if wos_name:
                collate = ' COLLATE NOCASE' if 'wos-name-nocase' in mode else ''
                if guild_search:
                    any_values.append(wos_name)
                    where_any_clauses.append('wosName = ?' + collate)
                else:
                    all_values.append(wos_name)
                    where_all_clauses.append('wosName = ?' + collate)

            where_query = ''
            if where_all_clauses:
                where_query = ' WHERE (' + ' AND '.join(where_all_clauses) + ')'
            if where_any_clauses:
                if where_query: where_query += ' AND'
                else : where_query = ' WHERE'

                where_query += ' (' + ' OR '.join(where_any_clauses) + ')'

            values = [*all_values, *any_values]

            limit_query = ''
            if limit and limit > 0:
                limit_query = ' LIMIT ?'
                values.append(limit)

            c.execute(f'SELECT id, timestamp, guildId, allianceId, discordId, wosId, wosName, status FROM wos_links{where_query}{limit_query}', values)
            rows = c.fetchall()
            if not rows: return []
            return [WosLink(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]) for row in rows]
        finally:
            if c: c.close()

    async def register_wos_link(self, guild_id: str, alliance_id: int | None, discord_id: str, wos_id: str, wos_name: str) -> WosLink:
        c = None
        try:
            ts = int(time.time())
            c = self.__con.cursor()

            c.execute(
                'INSERT INTO wos_links(timestamp, guildId, allianceId, discordId, wosId, wosName) VALUES (?, ?, ?, ?, ?, ?) RETURNING id',
                (ts, guild_id, alliance_id, discord_id, wos_id, wos_name)
            )
            row = c.fetchone()
            if not row: raise Exception('Unable to detect registered giftcode')
            self.__con.commit()
            return WosLink(row[0], ts, guild_id, alliance_id, discord_id, wos_id, wos_name, 'active')
        finally:
            if c: c.close()

    async def update_wos_link(
        self, wos_link: WosLink, timestamp: int | None = None,
        guild_id: str | None = None, alliance_id: int | None = None, discord_id: str | None = None,
        wos_id: str | None = None, wos_name: str | None = None,
        status: str | None = None) -> WosLink:
        c = None
        try:
            fields = []
            values = []
            if timestamp:
                fields.append('timestamp = ?')
                values.append(timestamp)
                wos_link.timestamp = timestamp
            if guild_id:
                fields.append('guildId = ?')
                values.append(guild_id)
                wos_link.guild_id = guild_id
            if alliance_id:
                alliance_id_value = None if alliance_id == -1 else alliance_id
                fields.append('allianceId = ?')
                values.append(alliance_id_value)
                wos_link.alliance_id = alliance_id_value
            if discord_id:
                fields.append('discordId = ?')
                values.append(discord_id)
                wos_link.discord_id = discord_id
            if wos_id:
                fields.append('wosId = ?')
                values.append(wos_id)
                wos_link.wos_id = wos_id
            if wos_name:
                fields.append('wosName = ?')
                values.append(wos_name)
                wos_link.wos_name = wos_name
            if status:
                fields.append('status = ?')
                values.append(status)
                wos_link.status = status

            if len(values) > 0:
                values.append(wos_link.id)
                c = self.__con.cursor()
                field_str = ', '.join(fields)
                c.execute(f'UPDATE wos_links SET {field_str} WHERE id = ?', values)
                self.__con.commit()

            return wos_link
        finally:
            if c: c.close()

    async def update_wos_request(self, join_request: JoinRequest,
            discord_message_id: str | None = None, status: str | None = None, handler_discord_id: str | None = None ) -> JoinRequest:
        c = None
        try:
            fields = []
            values = []
            if discord_message_id:
                fields.append('discordMessageId = ?')
                values.append(discord_message_id)
                join_request.discord_message_id = discord_message_id
            if status:
                fields.append('status = ?')
                values.append(status)
                join_request.status = status
            if handler_discord_id:
                fields.append('handlerDiscordId = ?')
                values.append(handler_discord_id)
                join_request.handler_discord_id = handler_discord_id


            if len(values) > 0:
                values.append(join_request.id)
                c = self.__con.cursor()
                field_str = ', '.join(fields)
                c.execute(f'UPDATE join_requests SET {field_str} WHERE id = ?', values)
                self.__con.commit()

            return join_request
        finally:
            if c: c.close()

    async def remove_alliance(self, alliance: Alliance) -> None:
        c = None
        try:
            c = self.__con.cursor()
            c.execute('UPDATE wos_links SET allianceId = ? WHERE allianceId = ?', (None, alliance.id))
            c.execute('DELETE FROM alliances WHERE id = ?', (alliance.id,))
            self.__con.commit()
        finally:
            if c: c.close()

    async def add_alliance(self, code: str, name: str, state: int, guild_id: str) -> Alliance:
        c = None
        try:
            c = self.__con.cursor()
            c.execute('INSERT INTO alliances(code, name, state, guildId) VALUES (?, ?, ?, ?) RETURNING id', (code, name, state, guild_id))
            row = c.fetchone()
            self.__con.commit()
            if not row: raise Exception('Unable to detect registered alliance')
            return Alliance(row[0], code, name, state, guild_id)
        finally:
            if c: c.close()

    async def get_alliances(
            self,
            id_: int | list[int] | None = None, code: str | None = None, name: str | None = None, state: int | None = None, guild_id: str | None = None,
            limit: int | None = None) -> list[Alliance]:
        c = None
        try:
            c = self.__con.cursor()
            where_clauses = []
            values = []
            if id_:
                try: where_clauses.append(f'id {auto_field(id_, values)}')
                except EmptyFieldException: return []
            if code:
                where_clauses.append('code = ? COLLATE NOCASE')
                values.append(code)
            if name:
                where_clauses.append('name = ?')
                values.append(name)
            if state:
                where_clauses.append('state = ?')
                values.append(state)
            if guild_id:
                where_clauses.append('guildId = ?')
                values.append(guild_id)

            where_query = ''
            if len(where_clauses) > 0: where_query = ' WHERE ' + ' AND '.join(where_clauses)

            limit_query = ''
            if limit and limit > 0:
                limit_query = ' LIMIT ?'
                values.append(limit)

            c.execute(f'SELECT id, code, name, state, guildId FROM alliances{where_query}{limit_query}', values)
            rows = c.fetchall()
            if not rows: return []
            return [Alliance(row[0], row[1], row[2], row[3], row[4]) for row in rows]
        finally:
            if c: c.close()

    async def get_giftcodes_by_code(self, codes: list[str]) -> list[Giftcode]:
        c = None
        try:
            c = self.__con.cursor()

            placeholders = ', '.join(['?'] * len(codes))
            c.execute(f'SELECT id, code, activeDate, expiryDate, closeDate FROM giftcodes WHERE code IN ({placeholders})', codes)
            rows = c.fetchall()
            if not rows: return []
            return [Giftcode(row[0], row[1], row[2], row[3], row[4]) for row in rows]
        finally:
            if c: c.close()

    async def get_active_giftcodes(self) -> list[Giftcode]:
        c = None
        try:
            c = self.__con.cursor()
            c.execute('SELECT id, code, activeDate, expiryDate, closeDate FROM giftcodes WHERE closeDate IS NULL or closeDate > ? or closeDate < 0', (int(time.time()),))
            rows = c.fetchall()
            if not rows: return []
            return [Giftcode(row[0], row[1], row[2], row[3], row[4]) for row in rows]
        finally:
            if c: c.close()

    async def register_giftcode(self, code: str, active_date: int, expiry_date: int | None = None, close_date: int | None = None) -> Giftcode:
        c = None
        try:
            c = self.__con.cursor()

            if active_date is not None: active_date = int(active_date)
            if expiry_date is not None: expiry_date = int(expiry_date)
            if close_date is not None: close_date = int(close_date)

            c.execute('INSERT INTO giftcodes(code, activeDate, expiryDate, closeDate) VALUES (?, ?, ?, ?) RETURNING id', (code, active_date, expiry_date, close_date))
            row = c.fetchone()
            if not row: raise Exception('Unable to detect registered giftcode')
            self.__con.commit()
            return Giftcode(row[0], code, active_date, expiry_date, close_date)
        finally:
            if c: c.close()

    async def update_giftcode(
            self, giftcode: Giftcode, code: str | None = None, active_date: int | None = None,
            expiry_date: int | None | UnsetField = UNSET, close_date: int | None | UnsetField = UNSET) -> Giftcode:
        c = None
        try:
            fields = []
            values = []

            if code:
                fields.append('code = ?')
                values.append(code)
                giftcode.code = code
            if active_date:
                fields.append('activeDate = ?')
                values.append(active_date)
                giftcode.active_date = active_date
            if not isinstance(expiry_date, UnsetField):
                fields.append(f'expiryDate {auto_field(expiry_date, values)}')
                giftcode.expiry_date = expiry_date
            if not isinstance(close_date, UnsetField):
                fields.append(f'closeDate {auto_field(close_date, values)}')
                giftcode.close_date = close_date

            if len(values) > 0:
                values.append(giftcode.id)
                c = self.__con.cursor()
                field_str = ', '.join(fields)
                c.execute(f'UPDATE giftcodes SET {field_str} WHERE id = ?', values)
                self.__con.commit()

            return giftcode
        finally:
            if c: c.close()

    async def register_giftcode_message(self, giftcode_id: int, guild_id: str, channel_id: str, message_id: str) -> GiftcodeMessage:
        c = None
        try:
            c = self.__con.cursor()

            c.execute('INSERT INTO giftcode_messages(giftcodeId, guildId, channelId, messageId) VALUES (?, ?, ?, ?) RETURNING id', (giftcode_id, guild_id, channel_id, message_id))
            row = c.fetchone()
            if not row: raise Exception('Unable to detect registered giftcode message')
            self.__con.commit()
            return GiftcodeMessage(row[0], giftcode_id, guild_id, channel_id, message_id)
        finally:
            if c: c.close()

    async def get_giftcode_messages(
        self, id_: int | None = None, giftcode_id: int | None = None, guild_id: str | None = None,
        channel_id: str | None = None, message_id: str | None = None, limit: int | None = None) -> list[GiftcodeMessage]:
        c = None
        try:
            where_clauses = []
            values = []
            if id_:
                where_clauses.append('id = ?')
                values.append(id_)
            if giftcode_id:
                where_clauses.append('giftcodeId = ?')
                values.append(giftcode_id)
            if guild_id:
                where_clauses.append('guildId = ?')
                values.append(guild_id)
            if channel_id:
                where_clauses.append('channelId = ?')
                values.append(channel_id)
            if message_id:
                where_clauses.append('messageId = ?')
                values.append(message_id)

            where_query = ''
            if len(where_clauses) > 0: where_query = ' WHERE ' + ' AND '.join(where_clauses)

            limit_query = ''
            if limit and limit > 0:
                limit_query = ' LIMIT ?'
                values.append(limit)

            c = self.__con.cursor()
            c.execute(f'''
                      SELECT id, giftcodeId, guildId, channelId, messageId
                      FROM giftcode_messages{where_query}{limit_query}''', values
            )
            rows = c.fetchall()
            if not rows: return []
            return [GiftcodeMessage(row[0], row[1], row[2], row[3], row[4]) for row in rows]
        finally:
            if c: c.close()

    async def register_join_request(self, discord_id: str, discord_username: str, discord_nickname: str, wos_id: str, wos_username: str, wos_alliance_id: int) -> JoinRequest:
        c = None
        try:
            c = self.__con.cursor()
            ts = int(time.time())
            c.execute('INSERT INTO join_requests(timestamp, discordId, discordUsername, discordNickname, wosId, wosUsername, wosAllianceId) VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id',
                      (ts, discord_id, discord_username, discord_nickname, wos_id, wos_username, wos_alliance_id))
            row = c.fetchone()
            if not row: raise Exception('Unable to detect registered join request')
            self.__con.commit()
            return JoinRequest(row[0], ts, discord_id, discord_username, discord_nickname, wos_id, wos_username, wos_alliance_id)
        finally:
            if c: c.close()

    async def update_join_request(self, join_request: JoinRequest,
            discord_message_id: str | None = None, status: str | None = None, handler_discord_id: str | None = None ) -> JoinRequest:
        c = None
        try:
            fields = []
            values = []
            if discord_message_id:
                fields.append('discordMessageId = ?')
                values.append(discord_message_id)
                join_request.discord_message_id = discord_message_id
            if status:
                fields.append('status = ?')
                values.append(status)
                join_request.status = status
            if handler_discord_id:
                fields.append('handlerDiscordId = ?')
                values.append(handler_discord_id)
                join_request.handler_discord_id = handler_discord_id


            if len(values) > 0:
                values.append(join_request.id)
                c = self.__con.cursor()
                field_str = ', '.join(fields)
                c.execute(f'UPDATE join_requests SET {field_str} WHERE id = ?', values)
                self.__con.commit()

            return join_request
        finally:
            if c: c.close()

    async def find_latest_join_request(self, discord_id: str, wos_id: str, wos_alliance_id: int) -> JoinRequest | None:
        c = None
        try:
            c = self.__con.cursor()
            c.execute('''
                      SELECT id, timestamp, discordId, discordUsername, discordNickname, wosId, wosUsername, wosAllianceId, status, handlerDiscordId
                      FROM join_requests WHERE discordId = ? AND wosId = ? AND wosAllianceId = ? ORDER BY timestamp DESC LIMIT 1''',
                      (discord_id, wos_id, wos_alliance_id))
            row = c.fetchone()
            if not row: return None
            self.__con.commit()
            return JoinRequest(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])
        finally:
            if c: c.close()

    async def get_join_requests(self, id_: str | None = None, limit: int | None = None) -> list[JoinRequest]:
        c = None
        try:
            where_clauses = []
            values = []
            if id_:
                where_clauses.append('id = ?')
                values.append(id_)

            where_query = ''
            if len(where_clauses) > 0: where_query = ' WHERE ' + ' AND '.join(where_clauses)

            limit_query = ''
            if limit and limit > 0:
                limit_query = ' LIMIT ?'
                values.append(limit)


            c = self.__con.cursor()
            c.execute(f'''
                      SELECT id, timestamp, discordId, discordUsername, discordNickname, wosId, wosUsername, wosAllianceId, discordMessageId, status, handlerDiscordId
                      FROM join_requests{where_query}{limit_query}''', values
            )
            rows = c.fetchall()
            if not rows: return []
            return [JoinRequest(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]) for row in rows]
        finally:
            if c: c.close()

    async def whitelist_state_add(self, guild_id: str, wos_state: str) -> None:
        c = None
        try:
            c = self.__con.cursor()
            c.execute('INSERT INTO wos_state_whitelist(guildId, wosState) VALUES(?, ?)', (guild_id, wos_state))
            self.__con.commit()
        finally:
            if c: c.close()

    async def whitelist_state_remove(self, guild_id: str, wos_state: str) -> None:
        c = None
        try:
            c = self.__con.cursor()
            c.execute('DELETE FROM wos_state_whitelist WHERE guildId = ? AND wosState = ?', (guild_id, wos_state))
            self.__con.commit()
        finally:
            if c: c.close()

    async def whitelist_state_list(self, guild_id: str) -> list[str]:
        c = None
        try:
            c = self.__con.cursor()
            c.execute('SELECT wosState FROM wos_state_whitelist WHERE guildId = ?', (guild_id,))
            rows = c.fetchall()
            if not rows: return []
            return [row[0] for row in rows]
        finally:
            if c: c.close()

    async def update_join_invite(self, join_invite: JoinInvite, executed: bool | None = None) -> JoinInvite:
        c = None
        try:
            fields = []
            values = []
            if isinstance(executed, bool):
                fields.append('executed = ?')
                values.append(1 if executed else 0)
                join_invite.executed = executed

            if len(values) > 0:
                values.append(join_invite.id)
                c = self.__con.cursor()
                field_str = ', '.join(fields)
                c.execute(f'UPDATE join_invites SET {field_str} WHERE id = ?', values)
                self.__con.commit()

            return join_invite
        finally:
            if c: c.close()

    async def create_join_invite(self, alliance_id: int, invite_code: str, creator_discord_id: str) -> JoinInvite:
        c = None
        timestamp = int(time.time())
        try:
            c = self.__con.cursor()
            c.execute('INSERT INTO join_invites(inviteCode, timestamp, wosAllianceId, creatorDiscordId) VALUES(?, ?, ?, ?) RETURNING id',
                      (invite_code, timestamp, alliance_id, creator_discord_id))
            row = c.fetchone()
            self.__con.commit()
            if not row: raise Exception('Unable to detect registered join invite')
            return JoinInvite(row[0], invite_code, timestamp, alliance_id, creator_discord_id, False)
        finally:
            if c: c.close()

    async def get_join_invite(
            self,
            id_: int | None = None,
            timestamp: int | None = None,
            invite_code: str | None = None,
            wos_alliance_id: int | None = None,
            creator_discord_id: str | None = None,
            executed: bool | None = None,
            limit: int | None = None) -> list[JoinInvite]:
        c = None
        try:
            c = self.__con.cursor()
            where_clauses = []
            values = []

            if id_:
                where_clauses.append(f'id = ?')
                values.append(id_)
            if timestamp:
                where_clauses.append('timestamp = ?')
                values.append(timestamp)
            if invite_code:
                where_clauses.append('inviteCode = ?')
                values.append(invite_code)
            if wos_alliance_id:
                where_clauses.append('wosAllianceId = ?')
                values.append(wos_alliance_id)
            if creator_discord_id:
                where_clauses.append('creatorDiscordId = ?')
                values.append(creator_discord_id)
            if isinstance(executed, bool):
                where_clauses.append('executed = ?')
                values.append(1 if executed else 0)

            where_query = ''
            if len(where_clauses) > 0: where_query = ' WHERE ' + ' AND '.join(where_clauses)

            limit_query = ''
            if limit and limit > 0:
                limit_query = ' LIMIT ?'
                values.append(limit)

            c.execute(f'SELECT id, inviteCode, timestamp, wosAllianceId, creatorDiscordId, executed FROM join_invites{where_query} ORDER BY timestamp DESC{limit_query}', values)
            rows = c.fetchall()
            if not rows: return []
            return [JoinInvite(row[0], row[1], row[2], row[3], row[4], bool(row[5])) for row in rows]
        finally:
            if c: c.close()

import json
import sqlite3
from typing import List, Optional

from graph import TokensResponse
from util import tomorrow

CREATE_SETTINGS = '''CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY UNIQUE,
    settings BLOB
);'''
CREATE_USERS = '''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY UNIQUE,
    user BLOB
);'''
CREATE_POLLS = '''CREATE TABLE IF NOT EXISTS polls (
    message_id INTEGER,
    guild_id INTEGER,
    channel_id INTEGER,
    user_id INTEGER,
    PRIMARY KEY(message_id, guild_id, channel_id, user_id)
)'''
CREATE_STARBOARD = '''CREATE TABLE IF NOT EXISTS starboard (
    orig_message_id INTEGER,
    guild_id INTEGER,
    message_id INTEGER,
    PRIMARY KEY(orig_message_id, guild_id)
)'''


class MessageTemplate:
    __slots__ = 'content', 'title', 'body'

    content: Optional[str]
    title: Optional[str]
    body: Optional[str]

    def __init__(
        self,
        content: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
    ):
        self.content = content
        self.title = title
        self.body = body

    @classmethod
    def load(cls, data: Optional[dict]) -> Optional['MessageTemplate']:
        if data is None:
            return
        obj = cls()
        obj.content = data.get('content')
        obj.title = data.get('title')
        obj.body = data.get('body')
        return obj

    def dump(self) -> dict:
        return {'content': self.content, 'title': self.title, 'body': self.body}


class Settings:
    __slots__ = (
        'quotes_channel',
        'teams_auth',
        'teams_channel',
        'teams_chat_id',
        'autoroles',
        'welcome_msg',
        'goodbye_msg',
        'greet_channel',
        'starboard_channel',
    )

    quotes_channel: Optional[int]
    teams_auth: Optional[TokensResponse]
    teams_channel: Optional[int]
    teams_chat_id: Optional[str]
    autoroles: List[int]
    welcome_msg: Optional[MessageTemplate]
    goodbye_msg: Optional[MessageTemplate]
    greet_channel: Optional[int]
    starboard_channel: Optional[int]

    def __init__(
        self,
        quotes_channel: Optional[int] = None,
        teams_auth: Optional[TokensResponse] = None,
        teams_channel: Optional[int] = None,
        teams_chat_id: Optional[str] = None,
        autoroles: Optional[List[int]] = None,
        welcome_msg: Optional[MessageTemplate] = None,
        goodbye_msg: Optional[MessageTemplate] = None,
        greet_channel: Optional[int] = None,
        starboard_channel: Optional[int] = None,
    ) -> None:
        self.quotes_channel = quotes_channel
        self.teams_auth = teams_auth
        self.teams_channel = teams_channel
        self.teams_chat_id = teams_chat_id
        self.autoroles = autoroles or []
        self.welcome_msg = welcome_msg
        self.goodbye_msg = goodbye_msg
        self.greet_channel = greet_channel
        self.starboard_channel = starboard_channel

    @classmethod
    def load(cls, data: bytes) -> 'Settings':
        d: dict = json.loads(data)
        obj = cls()
        obj.quotes_channel = d.get('quotes_channel')
        obj.teams_auth = d.get('teams_auth')
        obj.teams_channel = d.get('teams_channel')
        obj.teams_chat_id = d.get('teams_chat_id')
        obj.autoroles = d.get('autoroles') or []
        obj.welcome_msg = MessageTemplate.load(d.get('welcome_msg'))
        obj.goodbye_msg = MessageTemplate.load(d.get('goodbye_msg'))
        obj.greet_channel = d.get('greet_channel')
        obj.starboard_channel = d.get('starboard_channel')
        return obj

    def dump(self) -> bytes:
        return json.dumps(
            {
                'quotes_channel': self.quotes_channel,
                'teams_auth': self.teams_auth,
                'teams_channel': self.teams_channel,
                'teams_chat_id': self.teams_chat_id,
                'autoroles': self.autoroles,
                'welcome_msg': self.welcome_msg and self.welcome_msg.dump(),
                'goodbye_msg': self.goodbye_msg and self.goodbye_msg.dump(),
                'greet_channel': self.greet_channel,
                'starboard_channel': self.starboard_channel,
            }
        ).encode()


class User:
    __slots__ = (
        'chat_reset',
        'chat_used',
        'images_reset',
        'images_used',
        'timezone',
        'zlib_query',
    )

    chat_reset: float
    chat_used: int
    images_reset: float
    images_used: int
    timezone: Optional[int]
    zlib_query: Optional[str]  # ?remix_userid=...

    def __init__(
        self,
        chat_reset: Optional[float] = None,
        chat_used: int = 0,
        images_reset: Optional[float] = None,
        images_used: int = 0,
        timezone: Optional[int] = None,
        zlib_query: Optional[str] = None,
    ) -> None:
        self.chat_reset = chat_reset or tomorrow().timestamp()
        self.chat_used = chat_used
        self.images_reset = images_reset or tomorrow().timestamp()
        self.images_used = images_used
        self.timezone = timezone
        self.zlib_query = zlib_query

    @classmethod
    def load(cls, data: bytes) -> 'User':
        d: dict = json.loads(data)
        obj = cls()
        obj.chat_reset = d.get('chat_reset') or tomorrow().timestamp()
        obj.chat_used = d.get('chat_used', 0)
        obj.images_reset = d.get('images_reset') or tomorrow().timestamp()
        obj.images_used = d.get('images_used', 0)
        obj.timezone = d.get('timezone')
        obj.zlib_query = d.get('zlib_query')
        return obj

    def dump(self) -> bytes:
        return json.dumps(
            {
                'chat_reset': self.chat_reset,
                'chat_used': self.chat_used,
                'images_reset': self.images_reset,
                'images_used': self.images_used,
                'timezone': self.timezone,
                'zlib_query': self.zlib_query
            }
        ).encode()


class Database:
    def __init__(self, file: str = 'data.db') -> None:
        self.connection = sqlite3.connect(file)
        cur = self.cursor
        cur.execute(CREATE_SETTINGS)
        cur.execute(CREATE_USERS)
        cur.execute(CREATE_POLLS)
        cur.execute(CREATE_STARBOARD)
        self.connection.commit()

    @property
    def cursor(self) -> sqlite3.Cursor:
        return self.connection.cursor()

    def has_guild_settings(self, guild_id: int) -> bool:
        cur = self.cursor
        cur.execute('SELECT settings FROM settings WHERE id=?', (guild_id,))
        return cur.fetchone() is not None

    def get_guild_settings(self, guild_id: int) -> Settings:
        cur = self.cursor
        cur.execute('SELECT settings FROM settings WHERE id=?', (guild_id,))
        data = cur.fetchone()
        if data is not None:
            return Settings.load(data[0])
        return Settings()

    def set_guild_settings(self, guild_id: int, settings: Settings) -> None:
        data = settings.dump()
        cur = self.cursor
        params = [data, guild_id]
        if self.has_guild_settings(guild_id):
            sql = 'UPDATE settings SET settings=? WHERE id=?'
        else:
            sql = 'INSERT INTO settings(settings, id) VALUES(?, ?)'
        cur.execute(sql, params)
        self.connection.commit()

    def has_user(self, id: int) -> bool:
        cur = self.cursor
        cur.execute('SELECT user FROM users WHERE id=?', (id,))
        return cur.fetchone() is not None

    def get_user(self, id: int) -> User:
        cur = self.cursor
        cur.execute('SELECT user FROM users WHERE id=?', (id,))
        data = cur.fetchone()
        if data is not None:
            return User.load(data[0])
        return User()

    def set_user(self, id: int, user: User) -> None:
        data = user.dump()
        cur = self.cursor
        params = [data, id]
        if self.has_user(id):
            sql = 'UPDATE users SET user=? WHERE id=?'
        else:
            sql = 'INSERT INTO users(user, id) VALUES(?, ?)'
        cur.execute(sql, params)
        self.connection.commit()

    def has_poll(
        self, message_id: int, guild_id: int, channel_id: int, user_id: int
    ) -> bool:
        cur = self.cursor
        cur.execute(
            "SELECT '1' FROM polls WHERE message_id=? "
            'AND guild_id=? AND channel_id=? AND user_id=?',
            [message_id, guild_id, channel_id, user_id],
        )
        return cur.fetchone() is not None

    def add_poll(
        self, message_id: int, guild_id: int, channel_id: int, user_id: int
    ) -> None:
        cur = self.cursor
        cur.execute(
            'INSERT INTO polls(message_id, guild_id, '
            'channel_id, user_id) VALUES(?, ?, ?, ?)',
            [message_id, guild_id, channel_id, user_id],
        )
        self.connection.commit()

    def get_starboard_message(
        self, guild_id: int, orig_message_id: int
    ) -> Optional[int]:
        cur = self.cursor
        cur.execute(
            'SELECT message_id FROM starboard WHERE orig_message_id=? AND guild_id=?',
            [orig_message_id, guild_id],
        )
        data = cur.fetchone()
        if data:
            return data[0]

    def add_starboard_message(
        self, guild_id: int, orig_message_id: int, message_id: int
    ) -> None:
        cur = self.cursor
        cur.execute(
            'INSERT INTO starboard(orig_message_id, guild_id, '
            'message_id) VALUES(?, ?, ?)',
            [orig_message_id, guild_id, message_id],
        )
        self.connection.commit()

    def delete_starboard_message(self, guild_id: int, orig_message_id: int):
        cur = self.cursor
        cur.execute(
            'DELETE FROM starboard WHERE orig_message_id=? AND guild_id=?',
            [orig_message_id, guild_id],
        )
        self.connection.commit()

import json
import sqlite3
from typing import Optional
import time
from util import tomorrow
from graph import PollResponse

CREATE_SETTINGS = '''CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY UNIQUE,
    settings BLOB
);'''
CREATE_USERS = '''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY UNIQUE,
    user BLOB
);'''


class Settings:
    __slots__ = 'quotes_channel', 'teams_auth', 'teams_channel', 'teams_chat_id'

    quotes_channel: Optional[int]
    teams_auth: Optional[PollResponse]
    teams_channel: Optional[int]
    teams_chat_id: Optional[str]

    def __init__(
        self,
        quotes_channel: Optional[int] = None,
        teams_auth: Optional[PollResponse] = None,
        teams_channel: Optional[int] = None,
        teams_chat_id: Optional[str] = None,
    ) -> None:
        self.quotes_channel = quotes_channel
        self.teams_auth = teams_auth
        self.teams_channel = teams_channel
        self.teams_chat_id = teams_chat_id

    @classmethod
    def load(cls, data: bytes) -> 'Settings':
        d: dict = json.loads(data)
        obj = cls()
        obj.quotes_channel = d.get('quotes_channel')
        obj.teams_auth = d.get('teams_auth')
        obj.teams_channel = d.get('teams_channel')
        obj.teams_chat_id = d.get('teams_chat_id')
        return obj

    def dump(self) -> bytes:
        return json.dumps(
            {
                'quotes_channel': self.quotes_channel,
                'teams_auth': self.teams_auth,
                'teams_channel': self.teams_channel,
                'teams_chat_id': self.teams_chat_id,
            }
        ).encode()


class User:
    __slots__ = 'chat_reset', 'chat_used', 'images_reset', 'images_used', 'timezone'

    chat_reset: float
    chat_used: int
    images_reset: float
    images_used: int
    timezone: Optional[int]

    def __init__(
        self,
        chat_reset: Optional[float] = None,
        chat_used: int = 0,
        images_reset: Optional[float] = None,
        images_used: int = 0,
        timezone: Optional[int] = None,
    ) -> None:
        self.chat_reset = chat_reset or tomorrow().timestamp()
        self.chat_used = chat_used
        self.images_reset = images_reset or tomorrow().timestamp()
        self.images_used = images_used
        self.timezone = timezone

    @classmethod
    def load(cls, data: bytes) -> 'User':
        d: dict = json.loads(data)
        obj = cls()
        obj.chat_reset = d.get('chat_reset') or tomorrow().timestamp()
        obj.chat_used = d.get('chat_used', 0)
        obj.images_reset = d.get('images_reset') or tomorrow().timestamp()
        obj.images_used = d.get('images_used', 0)
        obj.timezone = d.get('timezone')
        return obj

    def dump(self) -> bytes:
        return json.dumps(
            {
                'chat_reset': self.chat_reset,
                'chat_used': self.chat_used,
                'images_reset': self.images_reset,
                'images_used': self.images_used,
                'timezone': self.timezone,
            }
        ).encode()


class Database:
    def __init__(self, file: str = 'data.db') -> None:
        self.connection = sqlite3.connect(file)
        cur = self.cursor
        cur.execute(CREATE_SETTINGS)
        cur.execute(CREATE_USERS)
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

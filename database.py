import json
import sqlite3
from typing import Optional

CREATE_SETTINGS = '''CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY UNIQUE,
    settings BLOB
);'''


class Settings:
    __slots__ = ('quotes_channel',)

    quotes_channel: Optional[int]

    def __init__(self, quotes_channel: Optional[int]=None):
        self.quotes_channel = quotes_channel

    @classmethod
    def load(cls, data: bytes):
        d: dict = json.loads(data)
        obj = cls()
        obj.quotes_channel = d.get('quotes_channel')
        return obj

    def dump(self) -> bytes:
        return json.dumps({'quotes_channel': self.quotes_channel}).encode()


class Database:
    def __init__(self, file: str = 'data.db'):
        self.connection = sqlite3.connect(file)
        cur = self.cursor
        cur.execute(CREATE_SETTINGS)
        self.connection.commit()

    @property
    def cursor(self):
        return self.connection.cursor()

    def get_guild_settings(self, guild_id: int) -> Settings:
        cur = self.cursor
        cur.execute('SELECT settings FROM settings WHERE id=?', (guild_id,))
        data = cur.fetchone()
        if data is not None:
            return Settings.load(data[0])
        return Settings()

    def set_guild_settings(self, guild_id: int, settings: Settings):
        data = settings.dump()
        cur = self.cursor
        params = [data, guild_id]
        if self.get_guild_settings(guild_id):
            sql = 'UPDATE settings SET settings=? WHERE id=?'
        else:
            sql = 'INSERT INTO settings(settings, id) VALUES(?, ?)'
        cur.execute(sql, params)
        self.connection.commit()

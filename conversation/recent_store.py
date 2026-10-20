"""Bounded SQLite conversation continuity, separate from confirmed knowledge."""
from contextlib import contextmanager
import sqlite3
import time


class RecentConversationStore:
    def __init__(self, path, limit=40, ttl_hours=24):
        self.path, self.limit = path, int(limit)
        self.ttl = float(ttl_hours) * 3600
        with self._connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS recent_conversation (id INTEGER PRIMARY KEY, speaker TEXT NOT NULL, content TEXT NOT NULL, route TEXT, created REAL NOT NULL)')

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def load(self):
        with self._connect() as db:
            db.execute('DELETE FROM recent_conversation WHERE created < ?', (time.time()-self.ttl,))
            rows = db.execute('SELECT speaker,content,route,created FROM recent_conversation ORDER BY id DESC LIMIT ?', (self.limit,)).fetchall()
        return [dict(speaker=s, content=c, route=r, created_at=t) for s,c,r,t in reversed(rows)]

    def append(self, speaker, content, route):
        with self._connect() as db:
            db.execute('INSERT INTO recent_conversation(speaker,content,route,created) VALUES (?,?,?,?)', (speaker,content,route,time.time()))
            db.execute('DELETE FROM recent_conversation WHERE created < ? OR id NOT IN (SELECT id FROM recent_conversation ORDER BY id DESC LIMIT ?)', (time.time()-self.ttl,self.limit))

    def clear(self):
        with self._connect() as db:
            db.execute('DELETE FROM recent_conversation')

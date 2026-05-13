import aiosqlite
import json
import os
from typing import Optional


class CacheManager:
    def __init__(self, db_path="scraper_cache.db"):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("PRAGMA journal_mode=WAL;")
        return self._db

    async def init_db(self):
        db = await self._get_db()
        await db.execute('''
            CREATE TABLE IF NOT EXISTS html_cache (
                url TEXT PRIMARY KEY,
                html TEXT,
                status_code INTEGER DEFAULT 200,
                content_length INTEGER
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS pagination_state (
                id INTEGER PRIMARY KEY,
                current_page INTEGER,
                current_url TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS parsed_items (
                url TEXT PRIMARY KEY,
                data TEXT
            )
        ''')
        await db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def clear_cache(self, mode="all"):
        if mode == "all":
            await self.close()
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            await self.init_db()
        elif mode == "state":
            db = await self._get_db()
            await db.execute("DELETE FROM pagination_state")
            await db.execute("DELETE FROM parsed_items")
            await db.commit()
        elif mode == "html":
            db = await self._get_db()
            await db.execute("DELETE FROM html_cache")
            await db.commit()

    async def get_html(self, url):
        db = await self._get_db()
        async with db.execute("SELECT html, content_length FROM html_cache WHERE url = ?", (url,)) as cursor:
            row = await cursor.fetchone()
            if row and row[1] > 0:
                return row[0]
            return None

    async def save_html(self, url, html, status_code=200):
        content_length = len(html) if html else 0
        db = await self._get_db()
        await db.execute(
            "INSERT OR REPLACE INTO html_cache (url, html, status_code, content_length) VALUES (?, ?, ?, ?)",
            (url, html, status_code, content_length)
        )
        await db.commit()

    async def save_state(self, current_page, current_url):
        db = await self._get_db()
        await db.execute(
            "INSERT OR REPLACE INTO pagination_state (id, current_page, current_url) VALUES (1, ?, ?)",
            (current_page, current_url)
        )
        await db.commit()

    async def load_state(self):
        db = await self._get_db()
        async with db.execute("SELECT current_page, current_url FROM pagination_state WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            if row:
                return {"current_page": row[0], "current_url": row[1]}
            return None

    async def save_item(self, url, data_dict):
        db = await self._get_db()
        await db.execute(
            "INSERT OR REPLACE INTO parsed_items (url, data) VALUES (?, ?)",
            (url, json.dumps(data_dict, ensure_ascii=False))
        )
        await db.commit()

    async def load_all_items(self):
        items = []
        db = await self._get_db()
        async with db.execute("SELECT data FROM parsed_items") as cursor:
            async for row in cursor:
                items.append(json.loads(row[0]))
        return items

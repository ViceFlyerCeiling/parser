import aiohttp
import asyncio

class StaticEngine:
    def __init__(self, config):
        self.config = config
        self.session = None
        self.proxy = None
        if config.proxy_pool:
            from proxy_manager import ProxyRotator
            self.proxy_rotator = ProxyRotator(config.proxy_pool)

    async def init_session(self):
        headers = {"User-Agent": "Mozilla/5.0 ..."}
        if self.config.headers:
            headers.update(self.config.headers)
        self.session = aiohttp.ClientSession(headers=headers)

    async def fetch(self, url: str, steps: list = None) -> str:
        if not self.session:
            await self.init_session()
        proxy = None
        if self.config.proxy_pool:
            proxy = self.proxy_rotator.get_next()
        timeout = aiohttp.ClientTimeout(total=30)
        async with self.session.get(url, proxy=proxy, timeout=timeout) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
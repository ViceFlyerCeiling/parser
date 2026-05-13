import random
from typing import List

class ProxyRotator:
    def __init__(self, proxies: List[str]):
        self.proxies = proxies
        self.current = 0
        self.blocked = set()

    def get_next(self) -> str:
        available = [p for p in self.proxies if p not in self.blocked]
        if not available:
            self.blocked.clear()
            available = self.proxies
        proxy = available[self.current % len(available)]
        self.current += 1
        return proxy

    def block_proxy(self, proxy: str):
        self.blocked.add(proxy)
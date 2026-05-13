import asyncio
import random
from playwright.async_api import async_playwright
from typing import Optional

class PlaywrightEngine:
    def __init__(self, config):
        self.config = config
        self.browser = None
        self.context = None
        self.proxy = None
        if config.proxy_pool:
            from proxy_manager import ProxyRotator
            self.proxy_rotator = ProxyRotator(config.proxy_pool)

    async def init_browser(self):
        self.playwright = await async_playwright().start()
        launch_args = {
            "headless": getattr(self.config, "headless", True),
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                f"--window-size={random.randint(1050,1920)},{random.randint(800,1080)}",
            ]
        }
        if self.proxy:
            launch_args["proxy"] = {
                "server": self.proxy,
                "username": "",
                "password": ""
            }
        self.browser = await self.playwright.chromium.launch(**launch_args)
        context_args = {
            "viewport": {"width": random.randint(1050,1920), "height": random.randint(800,1080)},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
            "locale": "en-US",
        }
        self.context = await self.browser.new_context(**context_args)
        # Подключаем stealth
        await self.context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        window.chrome = { runtime: {} };
        """)

    async def fetch(self, url: str, steps: list = None) -> str:
        if not self.context:
            await self.init_browser()
        page = await self.context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            await asyncio.sleep(2)  # Даем SPA время на перерисовку DOM
            if steps:
                for step in steps:
                    await self._execute_step(page, step)
            # Возвращаем HTML после всех шагов
            return await page.content()
        finally:
            await page.close()

    async def _execute_step(self, page, step):
        if hasattr(step, "dict"):
            step = step.dict()
        action = step.get("action")
        selector = step.get("selector")
        if action == "wait_for_selector":
            await page.wait_for_selector(selector)
        elif action == "click":
            await page.click(selector)
        elif action == "scroll":
            await page.evaluate(f"window.scrollBy(0, {step.get('amount', 500)})")
        elif action == "fill":
            await page.fill(selector, step.get("value", ""))
        # Добавляй другие экшены по необходимости

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright') and self.playwright:
            await self.playwright.stop()
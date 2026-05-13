import asyncio
import aiohttp


class TwoCaptchaSolver:
    def __init__(self, api_key):
        self.api_key = api_key

    async def solve_recaptcha(self, site_key, page_url):
        """Async reCAPTCHA solver via 2captcha API."""
        async with aiohttp.ClientSession() as session:
            # Submit task
            payload = {
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "json": 1
            }
            async with session.post("http://2captcha.com/in.php", data=payload) as resp:
                data = await resp.json(content_type=None)

            if data.get("status") != 1:
                return None

            captcha_id = data["request"]

            # Poll for result
            for _ in range(30):
                await asyncio.sleep(5)
                url = (
                    f"http://2captcha.com/res.php"
                    f"?key={self.api_key}&action=get&id={captcha_id}&json=1"
                )
                async with session.get(url) as resp:
                    result = await resp.json(content_type=None)
                if result.get("status") == 1:
                    return result["request"]
        return None
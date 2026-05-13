import asyncio
import argparse
import random
from bs4 import BeautifulSoup
from config_loader import load_config
from engines.playwright_engine import PlaywrightEngine
from engines.static_engine import StaticEngine
from pipeline import parse_items
from storage import save_items
from cache_manager import CacheManager

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Path to YAML config")
    parser.add_argument("--reset-cache", choices=["all", "state", "html"], help="Clear specific cache before starting")
    args = parser.parse_args()
    config = load_config(args.config)

    cache = CacheManager()
    await cache.init_db()

    if args.reset_cache:
        print(f"Resetting cache mode: {args.reset_cache}...")
        await cache.clear_cache(args.reset_cache)

    if config.engine == "playwright":
        engine = PlaywrightEngine(config)
    else:
        engine = StaticEngine(config)

    # Загрузка стейта
    state = await cache.load_state()
    start_page = 0
    current_url = config.start_url
    
    if state:
        start_page = state["current_page"]
        current_url = state["current_url"]
        print(f"Resuming from page {start_page + 1}: {current_url}")

    # Загружаем уже спарсенные (в том числе частично) записи
    all_items = await cache.load_all_items()
    # Создаем set из URL для быстрой проверки
    processed_urls = {item.get('link') for item in all_items if item.get('link')}

    if all_items:
        print(f"Loaded {len(all_items)} previously parsed items from cache.")

    try:
        # Здесь основной цикл пагинации
        for page in range(start_page, config.pagination.max_pages):
            html = await engine.fetch(current_url, config.steps)
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(html)
            items = parse_items(html, current_url, config)
            
            # Добавляем только новые элементы
            new_items = []
            for item in items:
                if item.get('link') not in processed_urls:
                    new_items.append(item)
                    all_items.append(item)
                    processed_urls.add(item.get('link'))
                    # Сохраняем базовые данные (без деталей пока) в БД
                    await cache.save_item(item.get('link'), item)


            # Поиск следующей страницы
            next_url = None
            if config.pagination.type == "next_selector" and config.pagination.selector:
                soup = BeautifulSoup(html, 'html.parser')
                next_element = soup.select_one(config.pagination.selector)
                if next_element and next_element.has_attr('href'):
                    from urllib.parse import urljoin
                    next_url = urljoin(current_url, next_element['href'])
            elif config.pagination.type == "url_param":
                import re
                match = re.search(r'page=(\d+)', current_url)
                if match:
                    next_page = int(match.group(1)) + 1
                    next_url = re.sub(r'page=\d+', f'page={next_page}', current_url)

            if not next_url:
                await cache.save_state(page + 1, current_url)
                break
            
            current_url = next_url
            await cache.save_state(page + 1, current_url)
            delay = random.uniform(config.delay["min"], config.delay["max"])
            print(f"Waiting {delay:.2f}s before next page...")
            await asyncio.sleep(delay)

        if config.detail_extraction:
            print(f"Starting detail extraction for {len(all_items)} items...")
            semaphore = asyncio.Semaphore(config.concurrency)
            from pipeline import parse_detail
            
            cache_hits = 0
            live_fetches = 0

            async def process_detail(item):
                nonlocal cache_hits, live_fetches
                if 'link' not in item or not item['link']:
                    return
                
                async with semaphore:
                    try:
                        detail_html = await cache.get_html(item['link'])
                        if detail_html:
                            cache_hits += 1
                        else:
                            live_fetches += 1
                            await asyncio.sleep(random.uniform(config.delay["min"], config.delay["max"]))
                            detail_html = await engine.fetch(item['link'], config.detail_steps)
                            await cache.save_html(item['link'], detail_html)
                            
                        detail_data = parse_detail(detail_html, item['link'], config.detail_extraction)
                        item.update(detail_data)
                        # Обновляем запись в БД со всеми полями
                        await cache.save_item(item['link'], item)
                    except Exception as e:
                        print(f"Error extracting details for {item['link']}: {e}")
                        item['error'] = str(e)
                        await cache.save_item(item['link'], item)
                        
            await asyncio.gather(*(process_detail(item) for item in all_items))
            print(f"Detail extraction finished: {cache_hits} from cache, {live_fetches} live fetches.")

        save_items(all_items, config.output)
        print(f"Собрано {len(all_items)} записей")
    finally:
        if hasattr(engine, 'close'):
            await engine.close()
        await cache.close()

if __name__ == "__main__":
    asyncio.run(main())
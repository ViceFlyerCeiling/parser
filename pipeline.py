from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

def parse_items(html: str, current_url: str, config) -> list:
    soup = BeautifulSoup(html, 'html.parser')
    items = []
    for card in soup.select(config.extraction.items_selector):
        item = {}
        for field_name, field_conf in config.extraction.fields.items():
            try:
                element = card.select_one(field_conf.selector)
                if not element:
                    if field_conf.optional:
                        item[field_name] = None
                    else:
                        raise ValueError(f"Missing element for {field_name}")
                    continue
                value = _extract_value(element, field_conf)
                if field_conf.regex:
                    match = re.search(field_conf.regex, value)
                    value = match.group(0) if match else ''
                if field_conf.transform:
                    value = _apply_transform(value, field_conf.transform, current_url)
                item[field_name] = value
            except Exception as e:
                if not field_conf.optional:
                    raise
        items.append(item)
    return items

def _extract_value(element, field_conf) -> str:
    if field_conf.attr == 'text':
        return element.get_text(strip=True)
    elif field_conf.attr == 'html':
        return element.decode_contents()
    else:
        return element.get(field_conf.attr, '')

def _apply_transform(value: str, transform_name: str, base_url: str) -> str:
    if transform_name == 'strip':
        return value.strip()
    elif transform_name == 'absolute_url':
        return urljoin(base_url, value)
    elif transform_name == 'clean_price':
        return re.sub(r'[^\d.]', '', value)
    return value

def parse_detail(html: str, current_url: str, detail_config: dict) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    detail_data = {}
    for field_name, field_conf in detail_config.items():
        try:
            element = soup.select_one(field_conf.selector)
            if not element:
                if field_conf.optional:
                    detail_data[field_name] = None
                else:
                    raise ValueError(f"Missing element for detail field {field_name}")
                continue
            value = _extract_value(element, field_conf)
            if field_conf.regex:
                match = re.search(field_conf.regex, value)
                value = match.group(0) if match else ''
            if field_conf.transform:
                value = _apply_transform(value, field_conf.transform, current_url)
            detail_data[field_name] = value
        except Exception as e:
            if not field_conf.optional:
                raise
    return detail_data
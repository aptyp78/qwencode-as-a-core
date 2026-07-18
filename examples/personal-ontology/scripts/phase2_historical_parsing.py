#!/usr/bin/env python3
"""
Фаза 2: Расширение парсинга на 2000-2019.
Источники: ВЭБ, ЭКСАР, РЭЦ, ранние интервью Фрадкова.
"""

import json
import requests
import re
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set
from bs4 import BeautifulSoup
import time


YANDEX_SEARCH_API_URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"
IAM_TOKEN = "YANDEX_IAM_TOKEN_PLACEHOLDER"
FOLDER_ID = "b1ga4lrfj1k4581lr0j2"


def search_yandex(query: str, page: int = 0) -> Dict:
    """Поиск через Yandex Search API v2."""
    try:
        headers = {"Authorization": f"Bearer {IAM_TOKEN}", "Content-Type": "application/json"}
        payload = {
            "query": {"search_type": "SEARCH_TYPE_RU", "query_text": query, "page": page},
            "folder_id": FOLDER_ID,
            "max_passages": 5
        }
        response = requests.post(YANDEX_SEARCH_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}


def parse_yandex_urls(response_data: Dict) -> List[str]:
    """Извлекает URL из ответа."""
    urls = []
    if "rawData" not in response_data:
        return urls
    try:
        raw_xml = base64.b64decode(response_data["rawData"]).decode("utf-8")
        root = ET.fromstring(raw_xml)
        for doc in root.findall(".//doc"):
            url = doc.findtext("url", "")
            if url:
                urls.append(url)
    except:
        pass
    return urls


def fetch_page(url: str) -> str:
    """Загружает страницу."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except:
        return ""


def extract_quotes_from_page(html: str, url: str) -> List[Dict]:
    """Извлекает высказывания из страницы."""
    quotes = []
    if not html:
        return quotes
    
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
        element.decompose()
    
    text = soup.get_text(separator=" ", strip=True)
    sentences = re.split(r'[.!?]+', text)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 30 or len(sentence) > 500:
            continue
        
        if "фрадков" in sentence.lower() or "пётр михайлович" in sentence.lower():
            quotes.append({
                "text": sentence,
                "source_url": url,
                "source_domain": url.split("/")[2] if "/" in url else "",
                "type": "real"
            })
    
    return quotes


def phase2_historical_parsing():
    """Фаза 2: Парсинг архивов 2000-2019."""
    
    print("=" * 60)
    print("Фаза 2: Расширение парсинга на 2000-2019")
    print("=" * 60)
    print()
    
    # Запросы для исторических данных
    queries = [
        'Фрадков Пётр ВЭБ 2005 2006 2007',
        'Фрадков Внешэкономбанк интервью',
        'Фрадков ЭКСАР 2007 2008 2009',
        'Фрадков Российский экспортный центр 2015',
        'Фрадков Пётр Михайлович 2000 2001 2002 2003',
        'Фрадков Дальневосточное морское пароходство',
        'Фрадков Пётр биография начало карьеры',
        'Фрадков ВЭБ структурное финансирование',
        'Фрадков ЭКСАР экспортное кредитование',
        'Фрадков РЭЦ генеральный директор',
        'Фрадков Пётр 2010 2011 2012 2013 2014',
        'Фрадков Пётр 2016 2017 назначение ПСБ',
        'Фрадков Михаил Ефимович сын карьера',
        'Фрадков Пётр диссертация кандидат экономических наук',
        'Фрадков Пётр МГИМО выпускник'
    ]
    
    # Собираем URL
    print("Сбор URL из исторических источников...")
    all_urls = set()
    
    for i, query in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] {query}")
        for page in range(3):
            response = search_yandex(query, page)
            urls = parse_yandex_urls(response)
            all_urls.update(urls)
        time.sleep(0.5)
    
    print(f"\n✓ Собрано URL: {len(all_urls)}")
    print()
    
    # Парсим страницы
    print("Парсинг страниц...")
    all_quotes = []
    
    for i, url in enumerate(list(all_urls)[:150], 1):
        if i % 20 == 0:
            print(f"  [{i}/150]")
        
        html = fetch_page(url)
        if html:
            quotes = extract_quotes_from_page(html, url)
            all_quotes.extend(quotes)
        
        time.sleep(0.3)
    
    print(f"\n✓ Обработано страниц: {min(len(all_urls), 150)}")
    print(f"✓ Извлечено высказываний: {len(all_quotes)}")
    
    # Убираем дубликаты
    unique_quotes = []
    seen = set()
    for q in all_quotes:
        text = q["text"].strip().lower()
        if text not in seen:
            seen.add(text)
            unique_quotes.append(q)
    
    print(f"✓ Уникальных: {len(unique_quotes)}")
    print()
    
    # Сохраняем
    output_path = "/Users/arturoceretnyj/personal-ontology/data/fradkov_historical_quotes.json"
    
    quotes_db = {
        "metadata": {
            "subject": "Фрадков Пётр Михайлович",
            "created": datetime.now().isoformat(),
            "period": "2000-2019",
            "total_quotes": len(unique_quotes),
            "type": "historical_real_quotes",
            "source": "Yandex Search + Page Parsing (historical)"
        },
        "quotes": []
    }
    
    for i, quote in enumerate(unique_quotes, 1):
        quotes_db["quotes"].append({
            "id": f"hist_quote_{i:03d}",
            "text": quote["text"],
            "date": "",
            "event": "",
            "topic": "",
            "source": quote.get("source_domain", ""),
            "url": quote.get("source_url", ""),
            "type": "real",
            "period": "2000-2019"
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(quotes_db, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Сохранено: {output_path}")
    print()
    print("=" * 60)
    print("Фаза 2 завершена")
    print("=" * 60)
    
    return quotes_db


if __name__ == "__main__":
    phase2_historical_parsing()

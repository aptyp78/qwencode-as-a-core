#!/usr/bin/env python3
"""
Масштабный парсинг полных страниц для сбора реальных высказываний.
Загружает URL из результатов Яндекс-поиска, парсит весь текст.
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


# Yandex Search API конфигурация
YANDEX_SEARCH_API_URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"
IAM_TOKEN = "YANDEX_IAM_TOKEN_PLACEHOLDER"
FOLDER_ID = "b1ga4lrfj1k4581lr0j2"


def search_yandex(query: str, page: int = 0) -> Dict:
    """Поиск через Yandex Search API v2."""
    try:
        headers = {
            "Authorization": f"Bearer {IAM_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": {
                "search_type": "SEARCH_TYPE_RU",
                "query_text": query,
                "page": page
            },
            "folder_id": FOLDER_ID,
            "max_passages": 5
        }
        
        response = requests.post(
            YANDEX_SEARCH_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    
    except Exception as e:
        print(f"  ⚠ Ошибка поиска: {e}")
        return {}


def parse_yandex_response_urls(response_data: Dict) -> List[str]:
    """Извлекает URL из ответа Yandex Search API."""
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
    
    except Exception as e:
        print(f"  ⚠ Ошибка парсинга URL: {e}")
    
    return urls


def collect_urls_from_search(queries: List[str], max_pages: int = 5) -> Set[str]:
    """Собирает URL из результатов поиска."""
    
    all_urls = set()
    
    for i, query in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] Запрос: {query}")
        
        for page in range(max_pages):
            response = search_yandex(query, page)
            urls = parse_yandex_response_urls(response)
            
            for url in urls:
                # Фильтруем только новостные и информационные сайты
                if any(domain in url for domain in [
                    "rbc.ru", "ria.ru", "tass.ru", "interfax.ru", 
                    "kommersant.ru", "vedomosti.ru", "iz.ru", "lenta.ru",
                    "rg.ru", "forbes.ru", "1tv.ru", "olimpic.ru",
                    "psbank.ru", "government.ru", "kremlin.ru"
                ]):
                    all_urls.add(url)
        
        print(f"  Собрано URL: {len(all_urls)}")
        time.sleep(0.5)  # Задержка между запросами
    
    return all_urls


def fetch_page(url: str) -> str:
    """Загружает страницу."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except Exception as e:
        return ""


def extract_quotes_from_page(html: str, url: str) -> List[Dict]:
    """Извлекает высказывания из полной страницы."""
    quotes = []
    
    if not html:
        return quotes
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Удаляем скрипты, стили, навигацию
    for element in soup(["script", "style", "nav", "header", "footer", "aside"]):
        element.decompose()
    
    # Получаем текст
    text = soup.get_text(separator=" ", strip=True)
    
    # Разбиваем на предложения
    sentences = re.split(r'[.!?]+', text)
    
    # Ищем предложения с упоминанием Фрадкова
    for sentence in sentences:
        sentence = sentence.strip()
        
        if len(sentence) < 30 or len(sentence) > 500:
            continue
        
        # Проверяем упоминание Фрадкова
        if "фрадков" in sentence.lower() or "пётр михайлович" in sentence.lower():
            quotes.append({
                "text": sentence,
                "source_url": url,
                "source_domain": url.split("/")[2] if "/" in url else "",
                "type": "real"
            })
    
    return quotes


def massive_parsing():
    """Масштабный парсинг для сбора реальных высказываний."""
    
    print("=" * 60)
    print("Масштабный парсинг для сбора реальных высказываний")
    print("=" * 60)
    print()
    
    # Запросы для поиска
    queries = [
        'Фрадков Пётр Михайлович интервью',
        'Фрадков ПСБ выступление',
        'Фрадков ПМЭФ',
        'Фрадков ВЭБ',
        'Фрадков ЭКСАР',
        'Фрадков ВФЛА лёгкая атлетика',
        'Фрадков ОПК гособоронзаказ',
        'Фрадков санкции',
        'Фрадков Путин встреча',
        'Фрадков трансформация банка',
        'Фрадков ИИ платформа',
        'Фрадков экспорт',
        'Фрадков финансовая архитектура',
        'Фрадков цифровая трансформация',
        'Фрадков стратегия',
        'Председатель ПСБ Фрадков заявление',
        'Промсвязьбанк Фрадков интервью',
        'Фрадков биография карьера',
        'Фрадков Михаил Ефимович сын',
        'Фрадков Промсвязьбанк 2026'
    ]
    
    # Собираем URL
    print("Фаза 1: Сбор URL из Яндекс-поиска")
    print("-" * 60)
    urls = collect_urls_from_search(queries, max_pages=5)
    print(f"\n✓ Собрано уникальных URL: {len(urls)}")
    print()
    
    # Парсим страницы
    print("Фаза 2: Парсинг страниц")
    print("-" * 60)
    
    all_quotes = []
    processed = 0
    
    for url in list(urls)[:200]:  # Ограничиваем 200 страницами для начала
        processed += 1
        
        if processed % 10 == 0:
            print(f"  Обработано: {processed}/{min(len(urls), 200)}")
        
        html = fetch_page(url)
        
        if html:
            quotes = extract_quotes_from_page(html, url)
            all_quotes.extend(quotes)
        
        time.sleep(0.3)  # Задержка между загрузками
    
    print(f"\n✓ Обработано страниц: {processed}")
    print(f"✓ Извлечено высказываний: {len(all_quotes)}")
    print()
    
    # Убираем дубликаты
    unique_quotes = []
    seen_texts = set()
    
    for quote in all_quotes:
        text_normalized = quote["text"].lower().strip()
        if text_normalized not in seen_texts:
            seen_texts.add(text_normalized)
            unique_quotes.append(quote)
    
    print("=" * 60)
    print("Результат:")
    print("=" * 60)
    print(f"Всего найдено: {len(all_quotes)}")
    print(f"Уникальных: {len(unique_quotes)}")
    print()
    
    # Сохраняем
    output_path = "/Users/arturoceretnyj/fradkov-ontology/data/fradkov_massive_parsed_quotes.json"
    
    quotes_db = {
        "metadata": {
            "subject": "Фрадков Пётр Михайлович",
            "created": datetime.now().isoformat(),
            "total_quotes": len(unique_quotes),
            "type": "real_quotes_massive_parsed",
            "source": "Yandex Search + Full Page Parsing",
            "description": "Реальные высказывания из масштабного парсинга"
        },
        "quotes": []
    }
    
    for i, quote in enumerate(unique_quotes, 1):
        quotes_db["quotes"].append({
            "id": f"parsed_quote_{i:03d}",
            "text": quote["text"],
            "date": "",
            "event": "",
            "topic": "",
            "source": quote.get("source_domain", ""),
            "url": quote.get("source_url", ""),
            "type": "real"
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(quotes_db, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Высказывания сохранены в {output_path}")
    
    return quotes_db


if __name__ == "__main__":
    massive_parsing()

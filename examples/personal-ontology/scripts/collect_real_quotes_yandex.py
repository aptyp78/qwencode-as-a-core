#!/usr/bin/env python3
"""
Массовый сбор РЕАЛЬНЫХ высказываний Фрадкова П.М. через Yandex Search API.
Парсит новости, интервью, выступления.
"""

import json
import requests
import re
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from urllib.parse import quote


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
            data = response.json()
            # Отладка: показываем структуру ответа
            if page == 0:
                print(f"    [Отладка] Ключи ответа: {list(data.keys())}")
                if "rawData" in data:
                    print(f"    [Отладка] rawData присутствует, длина: {len(data['rawData'])}")
            return data
        else:
            print(f"  ⚠ Ошибка API: {response.status_code}")
            print(f"    Ответ: {response.text[:200]}")
            return {}
    
    except Exception as e:
        print(f"  ⚠ Ошибка поиска: {e}")
        return {}


def parse_yandex_response(response_data: Dict) -> List[Dict]:
    """Парсит ответ Yandex Search API v2 (rawData в base64 XML)."""
    results = []
    
    if "rawData" not in response_data:
        print(f"  ⚠ Нет rawData в ответе")
        return results
    
    try:
        # Декодируем base64
        raw_xml = base64.b64decode(response_data["rawData"]).decode("utf-8")
        
        # Парсим XML
        root = ET.fromstring(raw_xml)
        
        # Ищем все документы
        for doc in root.findall(".//doc"):
            url = doc.findtext("url", "")
            title = doc.findtext("title", "")
            domain = doc.findtext("domain", "")
            
            # Ищем passages
            for passage in doc.findall(".//passage"):
                text = passage.text or ""
                if text:
                    results.append({
                        "url": url,
                        "title": title,
                        "domain": domain,
                        "text": text,
                        "date": ""
                    })
    
    except Exception as e:
        print(f"  ⚠ Ошибка парсинга XML: {e}")
    
    return results


def extract_quotes_from_text(text: str, person_name: str = "Фрадков") -> List[str]:
    """Извлекает цитаты из текста."""
    quotes = []
    
    # Паттерны для цитат
    patterns = [
        r'["""]([^"""]{20,300})["""]',  # Прямые цитаты в кавычках
        r'(?:сказал|заявил|отметил|подчеркнул|добавил|сообщил)[,:\s]+([^.!?]{20,300}[.!?])',
        r'(?:по словам|как отметил|как заявил|по мнению)\s+[^,]+[,]?\s+([^.!?]{20,300}[.!?])',
        r'—\s+([^.!?]{20,300}[.!?])',  # Цитаты после тире
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            quote = match.strip()
            # Фильтрация
            if len(quote) > 20 and len(quote) < 300:
                # Проверяем, что цитата связана с Фрадковым
                if person_name.lower() in text.lower() or "председатель" in text.lower() or "псб" in text.lower():
                    quotes.append(quote)
    
    # Убираем дубликаты
    return list(set(quotes))


def collect_quotes_from_search(query: str, max_pages: int = 5) -> List[Dict]:
    """Собирает цитаты из результатов поиска."""
    
    all_quotes = []
    
    for page in range(max_pages):
        print(f"  Страница {page + 1}/{max_pages}...")
        
        response = search_yandex(query, page)
        results = parse_yandex_response(response)
        
        print(f"    Найдено результатов: {len(results)}")
        
        for result in results:
            text = result["text"]
            quotes = extract_quotes_from_text(text)
            
            for quote in quotes:
                all_quotes.append({
                    "text": quote,
                    "source_url": result["url"],
                    "source_title": result["title"],
                    "source_domain": result["domain"],
                    "source_date": result["date"],
                    "query": query
                })
    
    return all_quotes


def collect_real_quotes_massively():
    """Массовый сбор реальных высказываний."""
    
    print("=" * 60)
    print("Массовый сбор РЕАЛЬНЫХ высказываний Фрадкова П.М.")
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
        'Фрадков Михаил сын',
        'Фрадков Виктор жена',
        'Фрадков биография карьера'
    ]
    
    all_quotes = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Запрос: {query}")
        quotes = collect_quotes_from_search(query, max_pages=3)
        print(f"  ✓ Собрано цитат: {len(quotes)}")
        all_quotes.extend(quotes)
    
    # Убираем дубликаты по тексту
    unique_quotes = []
    seen_texts = set()
    
    for quote in all_quotes:
        text_normalized = quote["text"].lower().strip()
        if text_normalized not in seen_texts:
            seen_texts.add(text_normalized)
            unique_quotes.append(quote)
    
    print()
    print("=" * 60)
    print("Результат сбора:")
    print("=" * 60)
    print(f"Всего найдено: {len(all_quotes)}")
    print(f"Уникальных: {len(unique_quotes)}")
    print()
    
    # Сохраняем
    output_path = "/Users/arturoceretnyj/personal-ontology/data/fradkov_real_quotes.json"
    
    quotes_db = {
        "metadata": {
            "subject": "Фрадков Пётр Михайлович",
            "created": datetime.now().isoformat(),
            "total_quotes": len(unique_quotes),
            "type": "real_quotes_only",
            "source": "Yandex Search API",
            "description": "Реальные высказывания из открытых источников"
        },
        "quotes": []
    }
    
    for i, quote in enumerate(unique_quotes, 1):
        quotes_db["quotes"].append({
            "id": f"real_quote_{i:03d}",
            "text": quote["text"],
            "date": quote.get("source_date", ""),
            "event": quote.get("source_title", ""),
            "topic": quote.get("query", ""),
            "source": quote.get("source_domain", ""),
            "url": quote.get("source_url", ""),
            "type": "real"
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(quotes_db, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Реальные высказывания сохранены в {output_path}")
    print()
    print("Следующие шаги:")
    print("  • Векторизовать реальные высказывания")
    print("  • Добавить в очищенный граф")
    print("  • Пересоздать векторно-графовое пространство")
    
    return quotes_db


if __name__ == "__main__":
    collect_real_quotes_massively()

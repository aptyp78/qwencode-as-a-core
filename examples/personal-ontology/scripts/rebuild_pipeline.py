#!/usr/bin/env python3
"""
Новый пайплайн сбора данных с сохранением source_url.
Правило: нет source_url → нет цитаты.

Процесс:
1. Яндекс-поиск → URL + сниппет
2. Fetch страницы → извлечение текста
3. Локальный LLM → извлечение цитат Фрадкова из текста
4. Валидация: cosine similarity цитаты с текстом страницы
5. Векторизация + сохранение в JSON

Использует: локальный LLM (извлечение цитат), локальные эмбеддинги.
"""

import json
import os
import re
import tempfile
import base64
import xml.etree.ElementTree as ET
import time
import requests
import numpy as np
import subprocess
from datetime import datetime
from urllib.parse import quote

# ═══ CONFIG ═══
YANDEX_URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"
FOLDER_ID = "b1ga4lrfj1k4581lr0j2"
OLLAMA_URL = "http://localhost:11434/api/generate"
EMBED_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "qwen3-embedding:8b"
LLM_MODEL = "qwen3-coder-next"
TOKEN_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".personal-ontology")
TOKEN_CACHE_FILE = os.path.join(TOKEN_CACHE_DIR, "yandex_token.json")
TOKEN_TTL = 11 * 3600  # 11 hours

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "rebuild_verified_quotes.json")

# ═══ SEARCH QUERIES ═══
# Приоритет: queries.json (автосгенерированные) → expanded_queries.json → хардкод
QUERIES_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "queries.json")
FALLBACK_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "expanded_queries.json")
if os.path.exists(QUERIES_FILE):
    with open(QUERIES_FILE) as f:
        QUERIES = json.load(f)
    print(f"✓ Запросы из config (автосгенерированные): {len(QUERIES)}")
elif os.path.exists(FALLBACK_FILE):
    with open(FALLBACK_FILE) as f:
        QUERIES = json.load(f)
    print(f"✓ Запросы из файла: {len(QUERIES)}")
else:
    QUERIES = [
    # ПСБ / Банк
    "Пётр Фрадков Промсвязьбанк интервью 2025",
    "Пётр Фрадков ПСБ гособоронзаказ",
    "Пётр Фрадков Промсвязьбанк цифровая трансформация",
    "Пётр Фрадков военная ипотека ПСБ",
    "Фрадков ПСБ поддержка участников спецоперации",

    # ВФЛА / Спорт
    "Пётр Фрадков ВФЛА президент лёгкая атлетика",
    "Пётр Фрадков World Athletics Олимпиада",
    "Фрадков беговые центры ПМЭФ",
    "Пётр Фрадков ОКР олимпийский комитет",

    # Экспорт / РЭЦ
    "Пётр Фрадков Российский экспортный центр",
    "Пётр Фрадков ЭКСАР несырьевой экспорт",

    # Технологии / Инновации
    "Пётр Фрадков технологический суверенитет",
    "Пётр Фрадков цифровой рубль блокчейн",
    "Пётр Фрадков импортозамещение промышленность",

    # Правительство
    "Пётр Фрадков Путин встреча",
    "Пётр Фрадков Мишустин совещание",
    "Пётр Фрадков Министерство обороны",

    # Форумы / Выступления
    "Пётр Фрадков ПМЭФ выступление 2026",
    "Пётр Фрадков форум интервью",
    "Пётр Фрадков РБК Ведомости интервью",

    # Санкции
    "Пётр Фрадков санкции ЕС США",
    "Fradkov PSB sanctions",

    # Биография
    "Пётр Михайлович Фрадков биография карьера",
]


def get_iam_token(force_refresh=False):
    """Получает IAM-токен с кэшированием (TTL 11 часов)."""
    os.makedirs(TOKEN_CACHE_DIR, exist_ok=True)

    # Проверяем кэш
    if not force_refresh and os.path.exists(TOKEN_CACHE_FILE):
        try:
            with open(TOKEN_CACHE_FILE) as f:
                cache = json.load(f)
            if time.time() - cache.get("timestamp", 0) < TOKEN_TTL:
                return cache.get("token")
        except:
            pass

    # Получаем новый токен
    try:
        result = subprocess.run(["yc", "iam", "create-token"], capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            token = result.stdout.strip()
            # Кэшируем
            with open(TOKEN_CACHE_FILE, "w") as f:
                json.dump({"token": token, "timestamp": time.time()}, f)
            return token
    except:
        pass
    return None


def search_yandex(query, token, page=0):
    try:
        resp = requests.post(YANDEX_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"query": {"search_type": "SEARCH_TYPE_RU", "query_text": query, "page": page},
                  "folder_id": FOLDER_ID, "max_passages": 3},
            timeout=20)
        if resp.status_code == 401:
            return []  # Trigger token refresh
        if resp.status_code != 200:
            return []

        data = resp.json()
        raw_b64 = data.get("rawData", "")
        if not raw_b64:
            return []

        raw_xml = base64.b64decode(raw_b64).decode("utf-8", errors="ignore")
        root = ET.fromstring(raw_xml)

        results = []
        for doc in root.findall(".//doc"):
            url_elem = doc.find("url")
            title_elem = doc.find("title")
            passages = doc.findall(".//passage")

            url = url_elem.text if url_elem is not None and url_elem.text else ""
            title = title_elem.text if title_elem is not None and title_elem.text else ""
            passage_text = " ".join(p.text for p in passages if p.text)

            if url and not url.startswith("https://yandex.ru/images"):
                results.append({"url": url, "title": title, "snippet": passage_text[:500]})

        return results
    except Exception as e:
        return []


def fetch_page(url):
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
        if resp.status_code != 200:
            return ""
        text = resp.text
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:8000]
    except:
        return ""


def extract_quotes(text, url):
    """Извлекает утверждения Фрадкова из текста через локальный LLM."""
    prompt = f"""Извлеки ключевые утверждения Петра Фрадкова (председатель ПСБ, президент ВФЛА) из текста.
Это могут быть не только прямые цитаты, но и пересказы его высказываний.
Верни СТРОГО JSON массив строк. Если утверждений нет — [].

Текст: {text[:3000]}

JSON: ["утверждение 1", "утверждение 2"]"""

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": LLM_MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 500}
        }, timeout=60)
        content = resp.json().get("response", "").strip()

        if "```" in content:
            lines = content.split("\n")
            content = "\n".join(l for l in lines if not l.strip().startswith("```"))

        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            quotes = json.loads(content[start:end])
            return [q for q in quotes if isinstance(q, str) and len(q) > 30]
    except:
        pass
    return []


def get_embedding(text):
    try:
        resp = requests.post(EMBED_URL, json={"model": EMBED_MODEL, "prompt": text}, timeout=30)
        return resp.json().get("embedding", [])
    except:
        return []


def cosine(v1, v2):
    a, b = np.array(v1), np.array(v2)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def validate_quote(quote_text, page_text):
    """Валидирует цитату через cosine similarity с текстом страницы."""
    q_emb = get_embedding(quote_text)
    if not q_emb:
        return 0.0

    max_sim = 0.0
    for i in range(0, len(page_text), 200):
        chunk = page_text[i:i+500]
        if len(chunk) < 50:
            continue
        c_emb = get_embedding(chunk)
        if not c_emb:
            continue
        sim = cosine(q_emb, c_emb)
        if sim > max_sim:
            max_sim = sim
    return max_sim


def main():
    print("=" * 60)
    print("ПЕРЕСБОРКА ГРАФА С ВАЛИДАЦИЕЙ")
    print("Правило: нет source_url → нет цитаты")
    print("=" * 60)
    print()

    token = get_iam_token()
    if not token:
        print("✗ IAM токен не получен")
        return
    print(f"✓ IAM токен: {token[:20]}...")

    # Загружаем существующие результаты
    all_quotes = []
    seen_urls = set()
    seen_texts = set()
    if os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH) as f:
            existing = json.load(f)
        all_quotes = existing
        for q in existing:
            seen_urls.add(q["source_url"])
            seen_texts.add(q["text"])
        print(f"✓ Загружено существующих цитат: {len(all_quotes)}")

    for qi, query in enumerate(QUERIES):
        print(f"\n[{qi+1}/{len(QUERIES)}] {query}")
        all_results = []
        for page in (0, 1, 2):  # multi-page: 3x results
            results = search_yandex(query, token, page=page)
            # Автообновление токена при 401
            if not results and page == 0:
                print(f"  Токен истёк, обновляю...")
                token = get_iam_token(force_refresh=True)
                if not token:
                    print(f"  ✗ Не удалось обновить токен")
                    break
                results = search_yandex(query, token, page=page)
            all_results.extend(results)
        new_results = [r for r in all_results if r["url"] not in seen_urls]
        for r in all_results:
            seen_urls.add(r["url"])

        if not new_results:
            print(f"  Новых URL: 0")
            continue

        print(f"  Новых URL: {len(new_results)}")

        for ri, result in enumerate(new_results[:3]):
            url = result["url"]
            page_text = fetch_page(url)
            if len(page_text) < 200:
                continue

            quotes = extract_quotes(page_text, url)
            if not quotes:
                continue

            for qt in quotes:
                if qt in seen_texts:
                    continue
                seen_texts.add(qt)

                # Валидация
                confidence = validate_quote(qt, page_text)

                # Векторизация
                emb = get_embedding(qt)
                if not emb:
                    continue

                all_quotes.append({
                    "text": qt,
                    "source_url": url,
                    "validation_confidence": round(confidence, 4),
                    "validation_status": "verified" if confidence >= 0.6 else "partial" if confidence >= 0.4 else "weak",
                    "embedding": emb,
                    "subject": "petr_m_fradkov",
                    "date_collected": datetime.now().isoformat()
                })

            print(f"    Стр. {ri+1}: {len(quotes)} цитат извлечено")

        # Сохраняем промежуточный результат
        with open(OUTPUT_PATH, "w") as f:
            json.dump(all_quotes, f, ensure_ascii=False, indent=2)

        print(f"  Всего: {len(all_quotes)} цитат")

    # Финальное сохранение
    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_quotes, f, ensure_ascii=False, indent=2)

    # Статистика
    verified = sum(1 for q in all_quotes if q["validation_status"] == "verified")
    partial = sum(1 for q in all_quotes if q["validation_status"] == "partial")
    weak = sum(1 for q in all_quotes if q["validation_status"] == "weak")

    print(f"\n{'='*60}")
    print(f"РЕЗУЛЬТАТ ПЕРЕСБОРКИ")
    print(f"{'='*60}")
    print(f"Всего цитат: {len(all_quotes)}")
    print(f"  verified (≥0.6): {verified}")
    print(f"  partial (≥0.4): {partial}")
    print(f"  weak (<0.4):    {weak}")
    print(f"  Все с source_url: ✅ {len(all_quotes)}/{len(all_quotes)}")
    print(f"\nСохранено: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
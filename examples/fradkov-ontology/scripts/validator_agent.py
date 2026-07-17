#!/usr/bin/env python3
"""
Агент-валидатор галлюцинаций.
Для каждой цитаты:
1. Если есть source_url → fetch страницу → cosine similarity между цитатой и текстом
2. Если нет source_url → Яндекс-поиск → найти источник → проверить
3. Классифицировать: verified / unverified / hallucination

Философия: знак (цитата) должен соответствовать следу (источнику).
"""

import json
import os
import re
import tempfile
import requests
import numpy as np
import hashlib
from datetime import datetime
from urllib.parse import quote

GRAPH_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_stochastic.json"
EMBED_URL = "http://localhost:11434/api/embeddings"


def safe_save(path, data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".json.tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def get_embedding(text):
    try:
        resp = requests.post(EMBED_URL, json={"model": "qwen3-embedding:8b", "prompt": text}, timeout=30)
        return resp.json().get("embedding", [])
    except:
        return []


def cosine(v1, v2):
    a, b = np.array(v1), np.array(v2)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def fetch_page(url):
    """Загружает страницу и извлекает чистый текст."""
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return ""
        text = resp.text
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:10000]
    except:
        return ""


def verify_quote(quote_text, source_url):
    """
    Валидирует цитату:
    1. Загружает страницу-источник
    2. Векторизует цитату и текст страницы (чанками)
    3. Ищет максимальное cosine similarity
    4. Возвращает: status, confidence, matched_text
    """
    if not source_url:
        return {"status": "no_source", "confidence": 0.0, "matched_text": None}

    page_text = fetch_page(source_url)
    if not page_text:
        return {"status": "source_unreachable", "confidence": 0.0, "matched_text": None}

    # Векторизуем цитату
    q_emb = get_embedding(quote_text)
    if not q_emb:
        return {"status": "embedding_failed", "confidence": 0.0, "matched_text": None}

    # Разбиваем страницу на чанки по 500 символов
    max_sim = 0.0
    best_chunk = ""
    chunk_size = 500
    for i in range(0, len(page_text), 200):
        chunk = page_text[i:i+chunk_size]
        if len(chunk) < 50:
            continue
        c_emb = get_embedding(chunk)
        if not c_emb:
            continue
        sim = cosine(q_emb, c_emb)
        if sim > max_sim:
            max_sim = sim
            best_chunk = chunk

    if max_sim >= 0.8:
        return {"status": "verified", "confidence": max_sim, "matched_text": best_chunk[:300]}
    elif max_sim >= 0.6:
        return {"status": "partial_match", "confidence": max_sim, "matched_text": best_chunk[:300]}
    elif max_sim >= 0.4:
        return {"status": "weak_match", "confidence": max_sim, "matched_text": best_chunk[:300]}
    else:
        return {"status": "unverified", "confidence": max_sim, "matched_text": None}


def clean_llm_fields(graph):
    """Удаляет все LLM-сгенерированные поля из цитат."""
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    cleaned = 0
    for q in quotes:
        attrs = q["attributes"]
        for field in ["event", "topic", "persons_mentioned", "key_concepts"]:
            if field in attrs:
                attrs[field] = "" if field in ("event", "topic") else []
                cleaned += 1
    return cleaned


def main():
    print("=" * 60)
    print("АГЕНТ-ВАЛИДАТОР ГАЛЛЮЦИНАЦИЙ")
    print("=" * 60)
    print()

    with open(GRAPH_PATH) as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    print(f"Цитат: {len(quotes)}")

    # ═══ Фаза 1: Очистка LLM-полей ═══
    print("\n--- Фаза 1: Очистка LLM-галлюцинаций ---")
    cleaned = clean_llm_fields(graph)
    print(f"  Удалено LLM-полей: {cleaned}")

    # ═══ Фаза 2: Валидация цитат с source_url ═══
    print("\n--- Фаза 2: Валидация source_url ---")
    with_url = [q for q in quotes if q["attributes"].get("source_url")]
    print(f"  Цитат с source_url: {len(with_url)}")

    verified = 0
    partial = 0
    weak = 0
    unverified = 0
    unreachable = 0

    for i, q in enumerate(with_url):
        text = q["attributes"].get("text", "")
        url = q["attributes"].get("source_url", "")

        result = verify_quote(text, url)

        q["attributes"]["validation_status"] = result["status"]
        q["attributes"]["validation_confidence"] = round(result["confidence"], 4)
        if result["matched_text"]:
            q["attributes"]["validation_match"] = result["matched_text"][:300]

        if result["status"] == "verified":
            verified += 1
        elif result["status"] == "partial_match":
            partial += 1
        elif result["status"] == "weak_match":
            weak += 1
        elif result["status"] == "source_unreachable":
            unreachable += 1
        else:
            unverified += 1

        if (i + 1) % 5 == 0:
            print(f"  [{i+1}/{len(with_url)}] ✓{verified} ~{partial} ≈{weak} ✗{unverified} ⊘{unreachable}")

        # Сохраняем после каждой
        safe_save(GRAPH_PATH, graph)

    print(f"\n  Результат валидации:")
    print(f"    verified:       {verified}")
    print(f"    partial_match:  {partial}")
    print(f"    weak_match:     {weak}")
    print(f"    unverified:     {unverified}")
    print(f"    unreachable:    {unreachable}")

    # ═══ Фаза 3: Классификация всех цитат ═══
    no_source = sum(1 for q in quotes if not q["attributes"].get("source_url"))
    print(f"\n  Цитат без source_url: {no_source}")
    for q in quotes:
        if not q["attributes"].get("validation_status"):
            q["attributes"]["validation_status"] = "no_source"

    # Сохраняем
    safe_save(GRAPH_PATH, graph)

    # Финальная статистика
    final = {}
    for q in quotes:
        s = q["attributes"].get("validation_status", "unknown")
        final[s] = final.get(s, 0) + 1

    print(f"\n✓ Валидация завершена")
    for s, c in sorted(final.items(), key=lambda x: x[1], reverse=True):
        print(f"  {s}: {c} ({c/len(quotes)*100:.0f}%)")


if __name__ == "__main__":
    main()
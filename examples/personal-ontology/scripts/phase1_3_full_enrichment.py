#!/usr/bin/env python3
"""
Полное LLM-обогащение метаданных через qwen3-coder-next (локально).
Таймаут 300s на запрос.
"""

import json
import requests
import re
from datetime import datetime


OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
MODEL = "qwen3-coder-next"
GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_phase1_2.json"
OUTPUT_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_phase1_enriched.json"


def enrich_quote(quote_text: str) -> dict:
    """Обогащение одной цитаты через LLM."""
    prompt = f'Определи метаданные для цитаты Фрадкова П.М.: {quote_text[:300]}. Ответь ТОЛЬКО JSON: {{"date": "YYYY-MM-DD или unknown", "topic": "1-3 слова", "event": "событие", "context": "1 предложение"}}'
    
    try:
        resp = requests.post(OLLAMA_CHAT_URL, json={
            'model': MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
            'stream': False,
            'options': {'temperature': 0.1, 'num_predict': 500}
        }, timeout=300)
        
        content = resp.json().get('message', {}).get('content', '')
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 60)
    print("Полное LLM-обогащение метаданных")
    print("=" * 60)
    print(f"Модель: {MODEL}")
    print(f"Таймаут: 300s")
    print()
    
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    need = [q for q in quotes if not q["attributes"].get("date") or not q["attributes"].get("topic")]
    
    print(f"Цитат всего: {len(quotes)}")
    print(f"Нуждаются в обогащении: {len(need)}")
    print()
    
    enriched = 0
    errors = 0
    
    for i, q in enumerate(need, 1):
        text = q["attributes"].get("text", "")
        if not text:
            continue
        
        if i % 10 == 0:
            print(f"  [{i}/{len(need)}] обогащено: {enriched}, ошибок: {errors}")
        
        meta = enrich_quote(text)
        
        if meta and "error" not in meta:
            if meta.get("topic", "unknown") != "unknown":
                q["attributes"]["topic"] = meta["topic"]
            if meta.get("date", "unknown") != "unknown":
                q["attributes"]["date"] = meta["date"]
            if meta.get("event", "unknown") != "unknown":
                q["attributes"]["event"] = meta["event"]
            if meta.get("context", "unknown") != "unknown":
                q["attributes"]["context"] = meta["context"]
            enriched += 1
        else:
            errors += 1
    
    # Статистика
    with_date = sum(1 for q in quotes if q["attributes"].get("date"))
    with_topic = sum(1 for q in quotes if q["attributes"].get("topic"))
    with_event = sum(1 for q in quotes if q["attributes"].get("event"))
    with_context = sum(1 for q in quotes if q["attributes"].get("context"))
    
    print()
    print("=" * 60)
    print("Результат:")
    print("=" * 60)
    print(f"Обогащено: {enriched}/{len(need)}")
    print(f"Ошибок: {errors}")
    print()
    print("Покрытие метаданных:")
    print(f"  С датой: {with_date}/{len(quotes)} ({with_date/len(quotes)*100:.1f}%)")
    print(f"  С темой: {with_topic}/{len(quotes)} ({with_topic/len(quotes)*100:.1f}%)")
    print(f"  С событием: {with_event}/{len(quotes)} ({with_event/len(quotes)*100:.1f}%)")
    print(f"  С контекстом: {with_context}/{len(quotes)} ({with_context/len(quotes)*100:.1f}%)")
    
    graph["metadata"]["phase1_3_completed"] = datetime.now().isoformat()
    graph["metadata"]["enrichment_stats"] = {
        "enriched": enriched,
        "errors": errors,
        "with_date": with_date,
        "with_topic": with_topic
    }
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"✓ Сохранено: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Фаза 1.3 только: LLM-обогащение метаданных.
Работает с уже векторизованным графом.
"""

import json
import requests
import re
from pathlib import Path
from datetime import datetime


OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
ENRICHMENT_MODEL = "qwen3-coder-next"
GRAPH_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_phase1_2.json"
OUTPUT_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_phase1_enriched.json"


def enrich_quote_metadata(quote_text: str, existing_meta: dict) -> dict:
    """LLM-обогащение метаданных цитаты."""
    
    prompt = f"""[РОЛЬ] Expert Metadata Enricher для онтологического графа деятельности Фрадкова П.М.

[ЗАДАЧА] Для следующей цитаты Фрадкова П.М. определи метаданные.

[ЦИТАТА]
{quote_text}

[СУЩЕСТВУЮЩИЕ ДАННЫЕ]
{json.dumps(existing_meta, ensure_ascii=False, indent=2)}

[ТРЕБУЕМЫЕ ПОЛЯ]
1. date — точная дата (YYYY-MM-DD) или период (YYYY), если неизвестно. Если нет данных — "unknown"
2. topic — тема (1-3 слова): финансовая архитектура, ОПК, спорт, экспорт, трансформация, санкции, образование, карьера, и т.д.
3. event — событие, в рамках которого сказано (ПМЭФ, встреча с Путиным, интервью, пресс-конференция, и т.д.)
4. context — контекст (1 предложение): почему это было сказано

[ОГРАНИЧЕНИЕ]
- Не выдумывай факты. Если не знаешь — пиши "unknown"
- Используй только информацию из цитаты и существующих данных
- Отвечай ТОЛЬКО в формате JSON, без пояснений

[ФОРМАТ ОТВЕТА]
{{"date": "...", "topic": "...", "event": "...", "context": "..."}}"""
    
    try:
        response = requests.post(
            OLLAMA_CHAT_URL,
            json={
                "model": ENRICHMENT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 500}
            },
            timeout=120
        )
        response.raise_for_status()
        
        content = response.json().get("message", {}).get("content", "")
        
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {}
    
    except Exception as e:
        return {"error": str(e)}


def main():
    print("=" * 60)
    print("Фаза 1.3: LLM-обогащение метаданных")
    print("=" * 60)
    print()
    
    # Загружаем граф (уже векторизованный)
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    total = len(quotes)
    
    need_enrichment = [q for q in quotes 
                       if not q["attributes"].get("date") or not q["attributes"].get("topic")]
    
    print(f"Цитат всего: {total}")
    print(f"Нуждаются в обогащении: {len(need_enrichment)}")
    print(f"Модель: {ENRICHMENT_MODEL}")
    print()
    
    enriched_count = 0
    
    for i, quote in enumerate(need_enrichment, 1):
        text = quote["attributes"].get("text", "")
        if not text:
            continue
        
        if i % 10 == 0:
            print(f"  [{i}/{len(need_enrichment)}]...")
        
        existing = {
            "source": quote["attributes"].get("source", ""),
            "url": quote["attributes"].get("url", ""),
            "date": quote["attributes"].get("date", ""),
            "event": quote["attributes"].get("event", ""),
            "topic": quote["attributes"].get("topic", "")
        }
        
        result = enrich_quote_metadata(text, existing)
        
        if result and "error" not in result:
            if not quote["attributes"].get("date") and result.get("date", "unknown") != "unknown":
                quote["attributes"]["date"] = result["date"]
            if not quote["attributes"].get("topic") and result.get("topic", "unknown") != "unknown":
                quote["attributes"]["topic"] = result["topic"]
            if not quote["attributes"].get("event") and result.get("event", "unknown") != "unknown":
                quote["attributes"]["event"] = result["event"]
            if result.get("context", "unknown") != "unknown":
                quote["attributes"]["context"] = result["context"]
            enriched_count += 1
    
    # Статистика
    with_date = sum(1 for q in quotes if q["attributes"].get("date"))
    with_topic = sum(1 for q in quotes if q["attributes"].get("topic"))
    with_event = sum(1 for q in quotes if q["attributes"].get("event"))
    with_context = sum(1 for q in quotes if q["attributes"].get("context"))
    
    print()
    print("=" * 60)
    print("Результат обогащения:")
    print("=" * 60)
    print(f"Обогащено: {enriched_count}/{len(need_enrichment)}")
    print()
    print("Покрытие метаданных:")
    print(f"  С датой: {with_date}/{total} ({with_date/total*100:.1f}%)")
    print(f"  С темой: {with_topic}/{total} ({with_topic/total*100:.1f}%)")
    print(f"  С событием: {with_event}/{total} ({with_event/total*100:.1f}%)")
    print(f"  С контекстом: {with_context}/{total} ({with_context/total*100:.1f}%)")
    
    # Сохраняем
    graph["metadata"]["phase1_3_completed"] = datetime.now().isoformat()
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"✓ Сохранено: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

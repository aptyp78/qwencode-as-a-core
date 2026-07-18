#!/usr/bin/env python3
"""
Фаза 1: Устранение критических разрывов.
1.1 — Векторизация всех цитат
1.2 — Вычисление семантических связей
1.3 — LLM-обогащение метаданных
"""

import json
import numpy as np
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple


OLLAMA_API_URL = "http://localhost:11434/api/embeddings"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
EMBEDDING_MODEL = "qwen3-embedding:8b"
ENRICHMENT_MODEL = "qwen3.6:35b"
GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_final_real.json"


def get_embedding(text: str) -> List[float]:
    """Получает embedding для текста."""
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("embedding", [])
    except Exception as e:
        return []


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Вычисляет косинусное сходство."""
    a = np.array(v1)
    b = np.array(v2)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def enrich_quote_metadata(quote_text: str, existing_meta: Dict) -> Dict:
    """
    LLM-обогащение метаданных цитаты.
    Определяет: дату, тему, событие, контекст.
    """
    
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
4. context — контекст (1 предложение): почему это было сказано, какая проблема обсуждалась

[ОГРАНИЧЕНИЕ]
- Не выдумывай факты. Если не знаешь — пиши "unknown"
- Используй только информацию из цитаты и существующих данных
- Отвечай в формате JSON

[ФОРМАТ ОТВЕТА]
{{"date": "...", "topic": "...", "event": "...", "context": "..."}}
"""
    
    try:
        response = requests.post(
            OLLAMA_CHAT_URL,
            json={
                "model": ENRICHMENT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        content = result.get("message", {}).get("content", "")
        
        # Парсим JSON из ответа
        # Ищем JSON-блок
        import re
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            enriched = json.loads(json_match.group())
            return enriched
        else:
            return {"date": "unknown", "topic": "unknown", "event": "unknown", "context": "unknown"}
    
    except Exception as e:
        return {"date": "unknown", "topic": "unknown", "event": "unknown", "context": f"error: {str(e)}"}


def phase1_vectorize(graph: Dict) -> Dict:
    """Фаза 1.1: Векторизация всех цитат."""
    
    print("=" * 60)
    print("Фаза 1.1: Векторизация всех цитат")
    print("=" * 60)
    print()
    
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    total = len(quotes)
    print(f"Цитат для векторизации: {total}")
    print()
    
    vectorized = 0
    failed = 0
    
    for i, quote in enumerate(quotes, 1):
        if i % 50 == 0:
            print(f"  [{i}/{total}]...")
        
        text = quote["attributes"].get("text", "")
        if not text:
            failed += 1
            continue
        
        embedding = get_embedding(text)
        
        if embedding:
            quote["embedding"] = embedding
            quote["embedding_model"] = EMBEDDING_MODEL
            vectorized += 1
        else:
            failed += 1
    
    print()
    print(f"✓ Векторизовано: {vectorized}/{total}")
    print(f"✗ Ошибок: {failed}")
    print()
    
    return graph


def phase1_semantic_connections(graph: Dict, threshold: float = 0.75, max_per_node: int = 5) -> Dict:
    """Фаза 1.2: Вычисление семантических связей."""
    
    print("=" * 60)
    print("Фаза 1.2: Вычисление семантических связей")
    print("=" * 60)
    print()
    
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote" and "embedding" in n]
    total = len(quotes)
    print(f"Цитат с embedding: {total}")
    print(f"Порог сходства: {threshold}")
    print()
    
    connections = []
    
    for i in range(total):
        if i % 50 == 0:
            print(f"  [{i}/{total}]...")
        
        q1 = quotes[i]
        
        # Находим похожие цитаты
        similarities = []
        for j in range(total):
            if i == j:
                continue
            
            q2 = quotes[j]
            sim = cosine_similarity(q1["embedding"], q2["embedding"])
            
            if sim >= threshold:
                similarities.append((j, sim))
        
        # Сортируем и берём топ-N
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        for j, sim in similarities[:max_per_node]:
            connections.append({
                "from": q1["id"],
                "to": quotes[j]["id"],
                "type": "semantically_related",
                "attributes": {
                    "similarity": round(sim, 4)
                }
            })
    
    # Убираем дубликаты (A→B и B→A)
    unique_connections = []
    seen_pairs = set()
    
    for conn in connections:
        pair = tuple(sorted([conn["from"], conn["to"]]))
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            unique_connections.append(conn)
    
    # Добавляем рёбра в граф
    graph["edges"].extend(unique_connections)
    
    print()
    print(f"✓ Создано семантических связей: {len(unique_connections)}")
    print()
    
    return graph


def phase1_enrich_metadata(graph: Dict) -> Dict:
    """Фаза 1.3: LLM-обогащение метаданных."""
    
    print("=" * 60)
    print("Фаза 1.3: LLM-обогащение метаданных")
    print("=" * 60)
    print()
    
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    total = len(quotes)
    
    # Считаем, сколько нужно обогатить
    need_enrichment = 0
    for q in quotes:
        attrs = q["attributes"]
        has_date = bool(attrs.get("date"))
        has_topic = bool(attrs.get("topic"))
        if not has_date or not has_topic:
            need_enrichment += 1
    
    print(f"Цитат всего: {total}")
    print(f"Нуждаются в обогащении: {need_enrichment}")
    print()
    
    enriched = 0
    
    for i, quote in enumerate(quotes, 1):
        attrs = quote["attributes"]
        has_date = bool(attrs.get("date"))
        has_topic = bool(attrs.get("topic"))
        
        if has_date and has_topic:
            continue
        
        if i % 20 == 0:
            print(f"  [{i}/{total}]...")
        
        text = attrs.get("text", "")
        if not text:
            continue
        
        # Существующие метаданные
        existing = {
            "source": attrs.get("source", ""),
            "url": attrs.get("url", ""),
            "date": attrs.get("date", ""),
            "event": attrs.get("event", ""),
            "topic": attrs.get("topic", "")
        }
        
        # LLM-обогащение
        enriched_meta = enrich_quote_metadata(text, existing)
        
        # Обновляем атрибуты (только если было unknown/пусто)
        if not has_date and enriched_meta.get("date", "unknown") != "unknown":
            attrs["date"] = enriched_meta["date"]
        if not has_topic and enriched_meta.get("topic", "unknown") != "unknown":
            attrs["topic"] = enriched_meta["topic"]
        if enriched_meta.get("event", "unknown") != "unknown" and not attrs.get("event"):
            attrs["event"] = enriched_meta["event"]
        if enriched_meta.get("context", "unknown") != "unknown":
            attrs["context"] = enriched_meta["context"]
        
        enriched += 1
    
    print()
    print(f"✓ Обогащено цитат: {enriched}")
    
    # Статистика после обогащения
    with_date = sum(1 for q in quotes if q["attributes"].get("date"))
    with_topic = sum(1 for q in quotes if q["attributes"].get("topic"))
    with_event = sum(1 for q in quotes if q["attributes"].get("event"))
    with_context = sum(1 for q in quotes if q["attributes"].get("context"))
    
    print()
    print("После обогащения:")
    print(f"  С датой: {with_date}/{total} ({with_date/total*100:.1f}%)")
    print(f"  С темой: {with_topic}/{total} ({with_topic/total*100:.1f}%)")
    print(f"  С событием: {with_event}/{total} ({with_event/total*100:.1f}%)")
    print(f"  С контекстом: {with_context}/{total} ({with_context/total*100:.1f}%)")
    print()
    
    return graph


def main():
    """Основная функция Фазы 1."""
    
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "  ФАЗА 1: УСТРАНЕНИЕ КРИТИЧЕСКИХ РАЗРЫВОВ".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    # Загружаем граф
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    print(f"Загружен граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    print()
    
    # Фаза 1.1: Векторизация
    graph = phase1_vectorize(graph)
    
    # Фаза 1.2: Семантические связи
    graph = phase1_semantic_connections(graph, threshold=0.75, max_per_node=5)
    
    # Фаза 1.3: LLM-обогащение
    graph = phase1_enrich_metadata(graph)
    
    # Обновляем метаданные
    graph["metadata"]["phase1_completed"] = datetime.now().isoformat()
    graph["metadata"]["phase1_results"] = {
        "vectorized_quotes": sum(1 for n in graph["nodes"] if n["type"] == "Quote" and "embedding" in n),
        "semantic_connections": sum(1 for e in graph["edges"] if e["type"] == "semantically_related"),
    }
    
    # Сохраняем
    output_path = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_phase1.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "  ФАЗА 1 ЗАВЕРШЕНА".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    print(f"Граф сохранён: {output_path}")
    print(f"Узлов: {len(graph['nodes'])}")
    print(f"Рёбер: {len(graph['edges'])}")


if __name__ == "__main__":
    main()

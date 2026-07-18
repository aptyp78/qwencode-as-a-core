#!/usr/bin/env python3
"""
Разрыв 1: Обогащение метаданных (оптимизированная версия).
Шаг 1: Прогоняет цитаты через LLM → сохраняет в JSON
Шаг 2: Batch-обновление Neo4j
Шаг 3: Re-migration в Qdrant
"""

import json
import requests
import sys
import time
import os
import tempfile
from datetime import datetime
from neo4j import GraphDatabase


def safe_save(path, data):
    """Атомарная запись JSON — через temp file + rename."""
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except:
        os.unlink(tmp_path)
        raise


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3-coder-next"
GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_stochastic.json"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "personal2026"

PROMPT = """Проанализируй цитату. Ответь СТРОГО JSON, без пояснений:
Цитата: "{text}"
Дата: {date}
JSON: {{"topic": "тема 2-4 слова", "event": "событие или пусто", "persons_mentioned": ["люди/орг"], "key_concepts": ["3-5 концептов"]}}
ТОЛЬКО JSON."""


def extract_meta(text, date=""):
    prompt = PROMPT.format(text=text[:300], date=date)
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 200}
        }, timeout=30)
        resp.raise_for_status()
        content = resp.json().get("response", "").strip()

        if "```" in content:
            lines = content.split("\n")
            content = "\n".join(l for l in lines if not l.strip().startswith("```"))

        start, end = content.find("{"), content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except Exception as e:
        return {"_error": str(e)[:100]}
    return {"_error": "parse_failed"}


def step1_enrich_json():
    """Обогащает JSON-граф метаданными через LLM."""
    print("=" * 60)
    print("Шаг 1: Обогащение метаданных через LLM")
    print("=" * 60)

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    need = [q for q in quotes if not q["attributes"].get("topic")]

    print(f"Всего цитат: {len(quotes)}")
    print(f"Нужно обогатить: {len(need)}")
    print()

    enriched, errors = 0, 0
    t0 = time.time()

    for i, q in enumerate(need):
        text = q["attributes"].get("text", "")
        if not text or len(text) < 20:
            continue

        date = q["attributes"].get("date", "")
        meta = extract_meta(text, date)

        if "_error" in meta:
            errors += 1
            if errors <= 3:
                print(f"  ✗ [{i+1}] {meta['_error']}")
        else:
            q["attributes"]["topic"] = meta.get("topic", "")
            q["attributes"]["event"] = meta.get("event", "")
            q["attributes"]["persons_mentioned"] = meta.get("persons_mentioned", [])
            q["attributes"]["key_concepts"] = meta.get("key_concepts", [])
            enriched += 1

        if (i + 1) % 20 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(need) - i - 1) / rate if rate > 0 else 0
            print(f"  [{i+1}/{len(need)}] ✓{enriched} ✗{errors} | {rate:.1f}/s | ETA: {remaining/60:.0f}min", flush=True)

            # Сохраняем прогресс (атомарно)
            safe_save(GRAPH_PATH, graph)

    # Финальное сохранение
    graph["metadata"]["metadata_enriched"] = datetime.now().isoformat()
    graph["metadata"]["metadata_enriched_count"] = enriched
    safe_save(GRAPH_PATH, graph)

    elapsed = time.time() - t0
    print()
    print(f"✓ Обогащено: {enriched}, ошибок: {errors}, время: {elapsed/60:.1f} мин")
    return graph


def step2_update_neo4j(graph):
    """Batch-обновление метаданных в Neo4j."""
    print()
    print("=" * 60)
    print("Шаг 2: Обновление Neo4j")
    print("=" * 60)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote" and n["attributes"].get("topic")]

    print(f"Цитат с метаданными: {len(quotes)}")

    # Batch через UNWIND
    BATCH = 200
    updated = 0

    with driver.session() as session:
        for i in range(0, len(quotes), BATCH):
            batch = quotes[i:i+BATCH]
            data = []
            for q in batch:
                a = q["attributes"]
                data.append({
                    "qid": q["id"],
                    "topic": a.get("topic", ""),
                    "event": a.get("event", ""),
                    "persons": a.get("persons_mentioned", []),
                    "concepts": a.get("key_concepts", [])
                })

            session.run("""
                UNWIND $data AS row
                MATCH (q:Quote {node_id: row.qid})
                SET q.topic = row.topic, q.event = row.event,
                    q.persons_mentioned = row.persons, q.key_concepts = row.concepts
            """, data=data)
            updated += len(batch)
            print(f"  [{updated}/{len(quotes)}]")

    driver.close()
    print(f"✓ Neo4j обновлён: {updated}")


def step3_show_stats(graph):
    """Показывает статистику по темам."""
    print()
    print("=" * 60)
    print("Статистика обогащения")
    print("=" * 60)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    with_topic = sum(1 for q in quotes if q["attributes"].get("topic"))
    with_event = sum(1 for q in quotes if q["attributes"].get("event"))
    with_persons = sum(1 for q in quotes if q["attributes"].get("persons_mentioned"))

    total = len(quotes)
    print(f"Покрытие метаданными:")
    print(f"  topic:    {with_topic}/{total} ({with_topic/total*100:.0f}%)")
    print(f"  event:    {with_event}/{total} ({with_event/total*100:.0f}%)")
    print(f"  persons:  {with_persons}/{total} ({with_persons/total*100:.0f}%)")

    # Топ тем
    topics = {}
    for q in quotes:
        t = q["attributes"].get("topic", "")
        if t:
            topics[t] = topics.get(t, 0) + 1

    if topics:
        print()
        print("Топ-20 тем:")
        for t, c in sorted(topics.items(), key=lambda x: x[1], reverse=True)[:20]:
            print(f"  {t}: {c}")


def main():
    graph = step1_enrich_json()
    step2_update_neo4j(graph)
    step3_show_stats(graph)

    print()
    print("✓ Разрыв 1 закрыт: метаданные обогащены")


if __name__ == "__main__":
    main()

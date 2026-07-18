#!/usr/bin/env python3
"""
Разрыв 4: NER — извлечение сущностей из цитат.
Для каждой цитаты: извлекает упомянутые организации, людей, события.
Создаёт рёбра MENTIONS_ORG, MENTIONS_PERSON, MENTIONS_EVENT в Neo4j.
"""

import json
import requests
import time
from datetime import datetime
from neo4j import GraphDatabase


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3-coder-next"
GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_stochastic.json"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "personal2026"

PROMPT = """Из цитаты извлеки упомянутые сущности. Ответь СТРОГО JSON:
Цитата: "{text}"
JSON: {{"persons": ["упомянутые люди"], "organizations": ["организации"], "events": ["события/форумы/конференции"], "places": ["места/страны"]}}
Только реальные имена из текста. ТОЛЬКО JSON."""


def extract_entities(text):
    prompt = PROMPT.format(text=text[:400])
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 200}
        }, timeout=120)
        resp.raise_for_status()
        content = resp.json().get("response", "").strip()

        if "```" in content:
            lines = content.split("\n")
            content = "\n".join(l for l in lines if not l.strip().startswith("```"))

        start, end = content.find("{"), content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except:
        pass
    return {}


def main():
    print("=" * 60)
    print("Разрыв 4: NER — извлечение сущностей")
    print("=" * 60)
    print()

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    # Берём выборку — все 1384 слишком долго, берём каждую 3-ю
    sample = quotes[::2]  # ~690 цитат

    print(f"Всего цитат: {len(quotes)}")
    print(f"Выборка для NER: {len(sample)}")
    print()

    # Собираем все сущности
    all_entities = {"persons": set(), "organizations": set(), "events": set(), "places": set()}
    quote_entities = {}  # quote_id → entities

    t0 = time.time()
    processed = 0

    for i, q in enumerate(sample):
        text = q["attributes"].get("text", "")
        if len(text) < 20:
            continue

        entities = extract_entities(text)
        qid = q["id"]
        quote_entities[qid] = entities

        for cat in all_entities:
            for e in entities.get(cat, []):
                if e and len(e) > 1:
                    all_entities[cat].add(e)

        processed += 1
        if (i + 1) % 50 == 0:
            elapsed = time.time() - t0
            rate = processed / elapsed if elapsed > 0 else 0
            eta = (len(sample) - i - 1) / rate / 60 if rate > 0 else 0
            print(f"  [{i+1}/{len(sample)}] {rate:.1f}/s | ETA: {eta:.0f}min | "
                  f"сущностей: P:{len(all_entities['persons'])} O:{len(all_entities['organizations'])} E:{len(all_entities['events'])}")

    elapsed = time.time() - t0
    print()
    print(f"Обработано: {processed}, время: {elapsed/60:.1f} мин")
    print()
    print(f"Извлечено уникальных сущностей:")
    print(f"  Персоны: {len(all_entities['persons'])}")
    print(f"  Организации: {len(all_entities['organizations'])}")
    print(f"  События: {len(all_entities['events'])}")
    print(f"  Места: {len(all_entities['places'])}")

    # Сохраняем сущности в JSON
    graph["metadata"]["ner_extracted"] = datetime.now().isoformat()
    graph["metadata"]["ner_counts"] = {k: len(v) for k, v in all_entities.items()}

    # Создаём узлы сущностей и рёбра в JSON (для миграции в Neo4j)
    new_nodes = []
    new_edges = []

    for cat, entities in all_entities.items():
        label_map = {
            "persons": "Person",
            "organizations": "Organization",
            "events": "Event",
            "places": "Place"
        }
        edge_map = {
            "persons": "MENTIONS_PERSON",
            "organizations": "MENTIONS_ORG",
            "events": "MENTIONS_EVENT",
            "places": "MENTIONS_PLACE"
        }

        for entity in entities:
            eid = f"ner_{cat}_{entity.lower().replace(' ', '_')[:50]}"
            new_nodes.append({
                "id": eid,
                "type": label_map[cat],
                "attributes": {"name": entity, "source": "ner_extraction"}
            })

            # Рёбра от цитат к сущности
            for qid, ents in quote_entities.items():
                if entity in ents.get(cat, []):
                    new_edges.append({
                        "from": qid,
                        "to": eid,
                        "type": edge_map[cat],
                        "attributes": {}
                    })

    graph["nodes"].extend(new_nodes)
    graph["edges"].extend(new_edges)

    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"\nДобавлено в граф:")
    print(f"  Новых узлов: {len(new_nodes)}")
    print(f"  Новых рёбер: {len(new_edges)}")

    # Обновляем Neo4j
    print()
    print("Обновление Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        # Создаём узлы сущностей
        for n in new_nodes:
            label = n["type"]
            name = n["attributes"]["name"]
            nid = n["id"]
            session.run(f"""
                MERGE (e:{label} {{node_id: $nid}})
                SET e.name = $name, e.source = 'ner_extraction'
            """, nid=nid, name=name)

        # Создаём рёбра (batch)
        BATCH = 500
        for i in range(0, len(new_edges), BATCH):
            batch = new_edges[i:i+BATCH]
            data = [{"from_id": e["from"], "to_id": e["to"], "etype": e["type"]} for e in batch]

            # Группируем по типу ребра
            by_type = {}
            for d in data:
                t = d["etype"]
                if t not in by_type:
                    by_type[t] = []
                by_type[t].append(d)

            for etype, items in by_type.items():
                session.run(f"""
                    UNWIND $data AS row
                    MATCH (q:Quote {{node_id: row.from_id}})
                    MATCH (e {{node_id: row.to_id}})
                    MERGE (q)-[r:{etype}]->(e)
                """, data=items)

            print(f"  Рёбра [{i+len(batch)}/{len(new_edges)}]")

    driver.close()

    print()
    print("✓ Разрыв 4 закрыт: NER-сущности в графе")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Очистка графа: удаление контента Михаила Ефимовича Фрадкова (отец).
Оставляем только Петра Михайловича Фрадкова (сын).

Классификация:
  - Явно Михаил → удалить
  - Явно Пётр → оставить
  - Неоднозначные → классифицировать по контексту
"""

import json
import re
import os
import tempfile
from datetime import datetime
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue


GRAPH_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_stochastic.json"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "fradkov2026"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "fradkov_quotes"


def safe_save(path, data):
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except:
        os.unlink(tmp_path)
        raise


def classify_quote(q):
    """
    Возвращает:
      'mikhail' — явно про Михаила (убрать)
      'petr' — явно про Петра (оставить)
      'ambiguous' — неясно
    """
    a = q.get("attributes", {})
    text = (a.get("text", "") or "").lower()
    topic = (a.get("topic", "") or "").lower()
    event = (a.get("event", "") or "").lower()
    source = (a.get("source_url", "") or "").lower()
    combined = f"{text} {topic} {event} {source}"

    # Явные маркеры МИХАИЛА
    mikhail_strong = [
        r'михаил\s+ефимович', r'м\.е\.\s*фрадков', r'м\.е\.',
        r'премьер.*фрадков', r'фрадков.*премьер',
        r'фрадков.*министр\s+промышленност', r'министр.*фрадков.*промышленност',
        r'директор\s+свр', r'свр.*директор',
        r'полпред.*фрадков', r'фрадков.*полпред',
        r'фрадков.*1950', r'1950.*фрадков',
        r'михаил\s+фрадков', r'фрадков\s+михаил',
        r'газета\s+коммерсантъ.*фрадков',
        r'фрадков.*инновационн.*прорыв',
        r'фрадков.*правительств', r'правительств.*фрадков',
    ]

    # Явные маркеры ПЕТРА
    petr_strong = [
        r'пётр\s+михайлович', r'петр\s+михайлович',
        r'п\.м\.\s*фрадков', r'петр\s+фрадков', r'пётр\s+фрадков',
        r'фрадков.*петр', r'фрадков.*пётр',
        r'промсвязьбанк', r'\bпсб\b',
        r'\bвфла\b', r'всероссийск.*федераци.*лёгк',
        r'российский\s+экспортн.*центр', r'\bрэк\b',
        r'\bэксар\b',
        r'фрадков.*псб', r'псб.*фрадков',
        r'фрадков.*атлетик', r'атлетик.*фрадков',
        r'фрадков.*спорт', r'спорт.*фрадков',
        r'фрадков.*экспорт', r'экспорт.*фрадков',
        r'замминистра\s+обороны.*фрадков',
    ]

    # Контекстные маркеры (слабые)
    mikhail_weak = [
        r'внешэкономбанк.*сша', r'оао\s+рэк',
        r'гособоронзаказ.*банк', r'санкци.*фрадков',
        r'фрадков.*санкци',
    ]

    petr_weak = [
        r'банк\s+развития.*экспорт', r'не сырьев.*экспорт',
        r'фрадков.*выступлени.*псб',
    ]

    # Проверяем сильные маркеры
    for p in mikhail_strong:
        if re.search(p, combined):
            return 'mikhail'

    for p in petr_strong:
        if re.search(p, combined):
            return 'petr'

    # Проверяем слабые маркеры
    for p in petr_weak:
        if re.search(p, combined):
            return 'petr'

    for p in mikhail_weak:
        if re.search(p, combined):
            return 'mikhail'

    return 'ambiguous'


def main():
    print("=" * 60)
    print("Очистка графа: удаление Михаила Ефимовича")
    print("=" * 60)
    print()

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]

    # Классифицируем
    to_remove = []
    to_keep = []
    ambiguous = []

    for q in quotes:
        cls = classify_quote(q)
        q["_classification"] = cls
        if cls == 'mikhail':
            to_remove.append(q)
        elif cls == 'petr':
            to_keep.append(q)
        else:
            ambiguous.append(q)

    print(f"Классификация:")
    print(f"  Михаил (удалить): {len(to_remove)}")
    print(f"  Пётр (оставить): {len(to_keep)}")
    print(f"  Неоднозначные: {len(ambiguous)}")
    print()

    # Неоднозначные — оставляем (они могут быть про Петра, просто без явных маркеров)
    # Но помечаем
    for q in ambiguous:
        q["attributes"]["subject"] = "uncertain"
    for q in to_keep:
        q["attributes"]["subject"] = "petr_m_fradkov"
    for q in to_remove:
        q["attributes"]["subject"] = "mikhail_e_fradkov"

    # Удаляем узлы Михаила
    remove_ids = set(q["id"] for q in to_remove)
    graph["nodes"] = [n for n in graph["nodes"] if n.get("id") not in remove_ids]

    # Удаляем рёбра, связанные с удалёнными узлами
    original_edges = len(graph["edges"])
    graph["edges"] = [e for e in graph["edges"]
                      if e["from"] not in remove_ids and e["to"] not in remove_ids]

    removed_edges = original_edges - len(graph["edges"])

    print(f"Удалено:")
    print(f"  Узлов: {len(remove_ids)}")
    print(f"  Рёбер: {removed_edges}")
    print(f"Осталось:")
    print(f"  Узлов: {len(graph['nodes'])}")
    print(f"  Рёбер: {len(graph['edges'])}")
    print()

    # Обновляем метаданные
    graph["metadata"]["cleaned"] = datetime.now().isoformat()
    graph["metadata"]["cleaned_removed_quotes"] = len(to_remove)
    graph["metadata"]["cleaned_removed_edges"] = removed_edges
    graph["metadata"]["subject"] = "Petr Mikhailovich Fradkov (Пётр Михайлович Фрадков)"

    # Сохраняем JSON
    safe_save(GRAPH_PATH, graph)
    print(f"✓ JSON сохранён")

    # Обновляем Neo4j
    print()
    print("Обновление Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        # Удаляем узлы Михаила и их рёбра
        result = session.run("""
            MATCH (q:Quote {subject: 'mikhail_e_fradkov'})
            DETACH DELETE q
            RETURN count(q) AS deleted
        """)
        deleted = result.single()["deleted"]
        print(f"  Удалено из Neo4j: {deleted} цитат")

        # Помечаем оставшиеся
        session.run("""
            MATCH (q:Quote)
            WHERE q.subject IS NULL OR q.subject = ''
            SET q.subject = 'petr_m_fradkov'
        """)
        print(f"  ✓ Оставшиеся помечены: subject = 'petr_m_fradkov'")

    driver.close()

    # Обновляем Qdrant
    print()
    print("Обновление Qdrant...")
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # Находим точки для удаления
    removed_count = 0
    for qid in remove_ids:
        try:
            # Находим point_id по quote_id
            results = qdrant.scroll(
                collection_name=COLLECTION,
                limit=1,
                filter=Filter(must=[FieldCondition(key="quote_id", match=MatchValue(value=qid))]),
            )
            points, _ = results
            if points:
                qdrant.delete(
                    collection_name=COLLECTION,
                    points_selector=[points[0].id]
                )
                removed_count += 1
        except Exception:
            pass

    print(f"  Удалено из Qdrant: {removed_count} точек")

    # Финальная статистика
    info = qdrant.get_collection(COLLECTION)
    print(f"  Осталось в Qdrant: {info.points_count}")

    print()
    print("=" * 60)
    print("✓ Очистка завершена")
    print("=" * 60)
    print()
    print(f"Субъект графа: Пётр Михайлович Фрадков")
    print(f"Цитат: {len([n for n in graph['nodes'] if n['type'] == 'Quote'])}")
    print(f"Узлов: {len(graph['nodes'])}")
    print(f"Рёбер: {len(graph['edges'])}")


if __name__ == "__main__":
    main()

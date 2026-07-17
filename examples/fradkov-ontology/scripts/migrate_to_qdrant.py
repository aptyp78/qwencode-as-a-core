#!/usr/bin/env python3
"""
Миграция векторов из JSON в Qdrant.
Создаёт коллекцию fradkov_quotes с 4096d embeddings + payload.
"""

import json
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue,
    PayloadSchemaType
)

GRAPH_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_stochastic.json"
COLLECTION_NAME = "fradkov_quotes"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333


def main():
    print("=" * 60)
    print("Миграция: JSON → Qdrant")
    print("=" * 60)
    print()

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote" and "embedding" in n]
    print(f"Цитат с embedding: {len(quotes)}")

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # Удаляем старую коллекцию если есть
    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in collections:
        client.delete_collection(COLLECTION_NAME)
        print(f"Удалена старая коллекция: {COLLECTION_NAME}")

    # Создаём коллекцию
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=4096, distance=Distance.COSINE)
    )
    print(f"✓ Коллекция создана: {COLLECTION_NAME} (4096d, cosine)")
    print()

    # Индексируем payload-поля для фильтрации
    for field in ["cluster", "year", "period", "source_domain"]:
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=PayloadSchemaType.INTEGER if field in ("cluster", "year") else PayloadSchemaType.KEYWORD
        )

    # Batch upload
    BATCH_SIZE = 100
    points = []
    for q in quotes:
        attrs = q.get("attributes", {})
        text = attrs.get("text", "")
        # Усекаем текст до 1000 символов для payload
        text_payload = text[:1000] if len(text) > 1000 else text

        # Извлекаем год из даты
        date = attrs.get("date", "")
        year = None
        if date and len(date) >= 4:
            try:
                year = int(date[:4])
            except ValueError:
                pass

        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=q["embedding"],
            payload={
                "quote_id": q["id"],
                "text": text_payload,
                "text_full": text,
                "date": date,
                "year": year,
                "period": attrs.get("period", ""),
                "cluster": attrs.get("cluster"),
                "source_url": attrs.get("source_url", ""),
                "source_domain": attrs.get("source_domain", ""),
                "event": attrs.get("event", ""),
                "topic": attrs.get("topic", ""),
                "node_type": q["type"]
            }
        )
        points.append(point)

        if len(points) >= BATCH_SIZE:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            points = []

    # Последний батч
    if points:
        client.upsert(collection_name=COLLECTION_NAME, points=points)

    info = client.get_collection(COLLECTION_NAME)
    print(f"✓ Загружено точек: {info.points_count}")
    print(f"  Размер вектора: {info.config.params.vectors.size}")
    print(f"  Метрика: {info.config.params.vectors.distance}")
    print()

    # Проверяем поиск
    if quotes:
        test_vec = quotes[0]["embedding"]
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=test_vec,
            limit=3
        )
        print("Тестовый поиск (top-3):")
        for r in results.points:
            print(f"  score={r.score:.4f} | {r.payload.get('text', '')[:80]}...")

    print()
    print("=" * 60)
    print("✓ Миграция в Qdrant завершена")
    print("=" * 60)


if __name__ == "__main__":
    main()

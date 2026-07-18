#!/usr/bin/env python3
"""
Ingestion Pipeline: загрузка нового документа в граф Фрадкова.

Принимает:
  - Текстовый файл (.txt, .md)
  - URL (через requests + BeautifulSoup)
  - Прямой текст через --text

Извлекает цитаты, векторизует, добавляет в Qdrant + Neo4j,
находит семантические связи, отчитывается о результатах.
"""

import argparse
import json
import re
import uuid
import sys
import requests
import numpy as np
from datetime import datetime
from collections import defaultdict

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from neo4j import GraphDatabase


# ── Config ──────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "qwen3-embedding:8b"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "personal_quotes"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "personal2026"
SIMILARITY_THRESHOLD = 0.75


# ── Helpers ─────────────────────────────────────────────────────────
def get_embedding(text: str) -> list[float]:
    resp = requests.post(OLLAMA_URL, json={"model": EMBEDDING_MODEL, "prompt": text}, timeout=60)
    resp.raise_for_status()
    return resp.json().get("embedding", [])


def cosine_sim(a, b):
    va, vb = np.array(a), np.array(b)
    na, nb = np.linalg.norm(va), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def extract_quotes_from_text(text: str) -> list[str]:
    """Извлекает содержательные фрагменты текста как цитаты."""
    # Разбиваем по предложениям
    sentences = re.split(r'(?<=[.!?])\s+', text)

    quotes = []
    for s in sentences:
        s = s.strip()
        # Фильтруем короткие и мусорные
        if len(s) < 30:
            continue
        if len(s) > 1000:
            # Разбиваем длинные на части по ~500 символов
            parts = [s[i:i+500] for i in range(0, len(s), 400)]
            quotes.extend(parts)
        else:
            quotes.append(s)

    return quotes


def extract_quotes_from_url(url: str) -> list[str]:
    """Загружает страницу и извлекает текст."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("Установите beautifulsoup4: pip install beautifulsoup4")
        sys.exit(1)

    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Удаляем скрипты, стили, навигацию
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()

    return extract_quotes_from_text(text)


def find_semantic_links(embedding: list[float], qdrant: QdrantClient, exclude_id: str) -> list[dict]:
    """Находит семантически близкие цитаты в Qdrant."""
    results = qdrant.query_points(
        collection_name=COLLECTION,
        query=embedding,
        limit=10
    )

    links = []
    for r in results.points:
        qid = r.payload.get("quote_id", "")
        if qid == exclude_id:
            continue
        if r.score >= SIMILARITY_THRESHOLD:
            links.append({
                "quote_id": qid,
                "text": (r.payload.get("text", ""))[:150],
                "similarity": round(r.score, 4),
                "cluster": r.payload.get("cluster")
            })
    return links


# ── Main Pipeline ───────────────────────────────────────────────────
def ingest(text: str, source_url: str = "", date: str = "", event: str = "",
           person_name: str = "Фрадков Михаил Ефимович"):

    print()
    print("=" * 60)
    print("Ingestion Pipeline")
    print("=" * 60)
    print()

    # 1. Извлечение цитат
    quotes = extract_quotes_from_text(text)
    print(f"Извлечено фрагментов: {len(quotes)}")
    if not quotes:
        print("Нет содержательных фрагментов для загрузки.")
        return

    # 2. Подключение
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    neo4j = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    # 3. Обработка каждой цитаты
    ingested = []
    total_links = 0
    cluster_hits = defaultdict(int)

    for i, quote_text in enumerate(quotes, 1):
        print(f"\n[{i}/{len(quotes)}] Векторизация...")

        # Векторизация
        embedding = get_embedding(quote_text)
        if not embedding:
            print(f"  ✗ Embedding пуст, пропуск")
            continue

        quote_id = f"ingested_{uuid.uuid4().hex[:12]}"
        year = None
        if date and len(date) >= 4:
            try:
                year = int(date[:4])
            except ValueError:
                pass

        # В Qdrant
        qdrant.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "quote_id": quote_id,
                    "text": quote_text[:1000],
                    "text_full": quote_text,
                    "date": date,
                    "year": year,
                    "period": "ingested",
                    "cluster": None,
                    "source_url": source_url,
                    "source_domain": "",
                    "event": event,
                    "topic": "",
                    "node_type": "Quote"
                }
            )]
        )

        # В Neo4j
        with neo4j.session() as session:
            session.run("""
                MERGE (q:Quote {node_id: $qid})
                SET q.text = $text, q.date = $date, q.year = $year,
                    q.source_url = $url, q.event = $event, q.period = 'ingested'
            """, qid=quote_id, text=quote_text[:5000], date=date, year=year,
                url=source_url, event=event)

            # Связь с персоной
            session.run("""
                MATCH (p:Person {name: $pname})
                MATCH (q:Quote {node_id: $qid})
                MERGE (p)-[:SAID]->(q)
            """, pname=person_name, qid=quote_id)

        # Семантические связи
        links = find_semantic_links(embedding, qdrant, quote_id)

        for link in links:
            with neo4j.session() as session:
                session.run("""
                    MATCH (a:Quote {node_id: $from_id})
                    MATCH (b:Quote {node_id: $to_id})
                    MERGE (a)-[r:SEMANTICALLY_RELATED]->(b)
                    SET r.similarity = $sim
                """, from_id=quote_id, to_id=link["quote_id"], sim=link["similarity"])

        total_links += len(links)
        ingested.append({
            "quote_id": quote_id,
            "text": quote_text[:200],
            "links_found": len(links)
        })

        if links:
            print(f"  ✓ {quote_id[:20]}... → {len(links)} семантических связей")
            for l in links[:3]:
                print(f"    sim={l['similarity']:.3f} cluster={l['cluster']} | {l['text'][:80]}...")
        else:
            print(f"  ✓ {quote_id[:20]}... → 0 связей (уникальная тема)")

    # 4. Отчёт
    print()
    print("=" * 60)
    print("Результат загрузки")
    print("=" * 60)
    print(f"  Цитат загружено: {len(ingested)}")
    print(f"  Семантических связей добавлено: {total_links}")
    print(f"  Источник: {source_url or 'прямой ввод'}")
    print(f"  Дата: {date or 'не указана'}")
    print()

    # Обновляем статистику
    info = qdrant.get_collection(COLLECTION)
    with neo4j.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        edge_count = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]

    print(f"  Qdrant: {info.points_count} точек")
    print(f"  Neo4j:  {node_count} узлов, {edge_count} рёбер")
    print()
    print("✓ Загрузка завершена")

    neo4j.close()


def main():
    parser = argparse.ArgumentParser(description="Загрузка документа в граф Фрадкова")
    parser.add_argument("--file", help="Путь к текстовому файлу")
    parser.add_argument("--url", help="URL страницы для загрузки")
    parser.add_argument("--text", help="Прямой текст для загрузки")
    parser.add_argument("--source", default="", help="URL-источник (для метаданных)")
    parser.add_argument("--date", default="", help="Дата (YYYY-MM-DD)")
    parser.add_argument("--event", default="", help="Событие/контекст")
    parser.add_argument("--person", default="Фрадков Михаил Ефимович", help="Имя персоны")

    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.url:
        text = "\n".join(extract_quotes_from_url(args.url))
        if not args.source:
            args.source = args.url
    elif args.text:
        text = args.text
    else:
        print("Укажите --file, --url или --text")
        sys.exit(1)

    ingest(text, source_url=args.source, date=args.date,
           event=args.event, person_name=args.person)


if __name__ == "__main__":
    main()

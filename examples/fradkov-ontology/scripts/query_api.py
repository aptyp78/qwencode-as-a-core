#!/usr/bin/env python3
"""
Query API: стохастическое сопоставление новых документов с графом Фрадкова.

Endpoints:
  POST /query       — основной запрос: текст → анализ + сопоставление
  POST /ingest      — загрузка нового документа в граф
  GET  /stats       — статистика графа
  GET  /clusters    — список кластеров с примерами
  GET  /transitions — матрица переходов
"""

import json
import uuid
import requests
import numpy as np
from datetime import datetime
from typing import Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from neo4j import GraphDatabase


# ── Config ──────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "qwen3-embedding:8b"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "fradkov_quotes"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "fradkov2026"
GRAPH_JSON = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_stochastic.json"

# ── Init ────────────────────────────────────────────────────────────
app = FastAPI(title="Fradkov Ontology API", version="1.0.0")
qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

# Загружаем стохастическую модель
with open(GRAPH_JSON, "r", encoding="utf-8") as f:
    _graph = json.load(f)
_stochastic = _graph.get("metadata", {}).get("stochastic_layer", {})
_transition_matrix = _stochastic.get("transition_matrix", {})


# ── Helpers ─────────────────────────────────────────────────────────
def get_embedding(text: str) -> list[float]:
    resp = requests.post(OLLAMA_URL, json={"model": EMBEDDING_MODEL, "prompt": text}, timeout=60)
    resp.raise_for_status()
    return resp.json().get("embedding", [])


def cosine_sim(a, b):
    va, vb = np.array(a), np.array(b)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def get_graph_context(quote_ids: list[str], cluster: Optional[int] = None) -> dict:
    """Извлекает контекст из Neo4j для найденных цитат."""
    context = {"entities": [], "activities": [], "related_quotes": []}

    with neo4j_driver.session() as session:
        # Связанные сущности
        ids_str = ", ".join(f"'{qid}'" for qid in quote_ids[:20])
        result = session.run(f"""
            MATCH (q:Quote)-[r]-(entity)
            WHERE q.node_id IN [{ids_str}]
            AND NOT entity:Quote
            RETURN DISTINCT labels(entity)[0] AS type, entity.name AS name,
                   entity.node_id AS id, type(r) AS relation
            LIMIT 30
        """)
        for r in result:
            context["entities"].append({
                "type": r["type"],
                "name": r["name"],
                "id": r["id"],
                "relation": r["relation"]
            })

        # Activities
        result = session.run(f"""
            MATCH (q:Quote)-[:BELONGS_TO_ACTIVITY]->(a:Activity)
            WHERE q.node_id IN [{ids_str}]
            RETURN DISTINCT a.name AS name, a.node_id AS id
        """)
        for r in result:
            context["activities"].append({"name": r["name"], "id": r["id"]})

        # Семантически связанные цитаты (из Neo4j)
        result = session.run(f"""
            MATCH (q:Quote)-[:SEMANTICALLY_RELATED]-(related:Quote)
            WHERE q.node_id IN [{ids_str}]
            RETURN DISTINCT related.node_id AS id, related.text AS text,
                   related.cluster AS cluster, related.date AS date
            LIMIT 15
        """)
        for r in result:
            context["related_quotes"].append({
                "id": r["id"],
                "text": (r["text"] or "")[:200],
                "cluster": r["cluster"],
                "date": r["date"]
            })

    # Стохастические переходы из текущего кластера
    if cluster is not None and _transition_matrix:
        cluster_key = str(cluster)
        if cluster_key in _transition_matrix:
            transitions = _transition_matrix[cluster_key]
            sorted_t = sorted(transitions.items(), key=lambda x: x[1], reverse=True)[:5]
            context["probable_transitions"] = [
                {"to_cluster": int(k), "probability": v}
                for k, v in sorted_t
            ]

    return context


# ── Models ──────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    text: str
    top_k: int = 10
    min_similarity: float = 0.4
    cluster_filter: Optional[int] = None

class QueryResponse(BaseModel):
    query_text: str
    query_embedding_dim: int
    matches: list[dict]
    graph_context: dict
    dominant_cluster: Optional[int]
    confidence: float
    analysis: str

class IngestRequest(BaseModel):
    text: str
    source_url: str = ""
    date: str = ""
    event: str = ""

class StatsResponse(BaseModel):
    total_quotes: int
    total_entities: int
    total_edges: int
    clusters: int
    years_covered: str
    qdrant_points: int
    neo4j_nodes: int
    neo4j_edges: int


# ── Endpoints ───────────────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    """Стохастическое сопоставление текста с графом."""
    # 1. Векторизация запроса
    try:
        embedding = get_embedding(req.text)
    except Exception as e:
        raise HTTPException(500, f"Embedding failed: {e}")

    if not embedding:
        raise HTTPException(500, "Empty embedding")

    # 2. Поиск в Qdrant
    search_params = {"query": embedding, "limit": req.top_k}

    if req.cluster_filter is not None:
        search_params["query_filter"] = Filter(
            must=[FieldCondition(key="cluster", match=MatchValue(value=req.cluster_filter))]
        )

    results = qdrant.query_points(
        collection_name=COLLECTION,
        **search_params
    )

    matches = []
    clusters_found = defaultdict(int)

    for r in results.points:
        if r.score < req.min_similarity:
            continue
        p = r.payload
        matches.append({
            "quote_id": p.get("quote_id"),
            "text": (p.get("text", ""))[:300],
            "score": round(r.score, 4),
            "date": p.get("date", ""),
            "cluster": p.get("cluster"),
            "source_url": p.get("source_url", ""),
            "topic": p.get("topic", "")
        })
        if p.get("cluster") is not None:
            clusters_found[p["cluster"]] += 1

    # 3. Определяем доминирующий кластер
    dominant_cluster = None
    if clusters_found:
        dominant_cluster = max(clusters_found, key=clusters_found.get)

    # 4. Confidence = средняя similarity топ-3
    confidence = 0.0
    if matches:
        top_scores = [m["score"] for m in matches[:3]]
        confidence = round(sum(top_scores) / len(top_scores), 4)

    # 5. Графовый контекст
    quote_ids = [m["quote_id"] for m in matches if m["quote_id"]]
    graph_context = get_graph_context(quote_ids, dominant_cluster)

    # 6. Формируем анализ
    analysis_parts = []
    if matches:
        analysis_parts.append(f"Найдено {len(matches)} семантических совпадений (confidence: {confidence}).")
    if dominant_cluster is not None:
        analysis_parts.append(f"Доминирующий кластер: {dominant_cluster}.")
    if "probable_transitions" in graph_context:
        trans = graph_context["probable_transitions"]
        if trans:
            next_clusters = [str(t["to_cluster"]) for t in trans[:3]]
            analysis_parts.append(f"Вероятные переходы: кластеры {', '.join(next_clusters)}.")
    if graph_context["entities"]:
        entity_names = [e["name"] for e in graph_context["entities"][:5] if e.get("name")]
        if entity_names:
            analysis_parts.append(f"Связанные сущности: {', '.join(entity_names)}.")
    if graph_context["activities"]:
        act_names = [a["name"] for a in graph_context["activities"][:3]]
        analysis_parts.append(f"Виды деятельности: {', '.join(act_names)}.")

    analysis = " ".join(analysis_parts) if analysis_parts else "Совпадений не найдено."

    return QueryResponse(
        query_text=req.text[:200],
        query_embedding_dim=len(embedding),
        matches=matches,
        graph_context=graph_context,
        dominant_cluster=dominant_cluster,
        confidence=confidence,
        analysis=analysis
    )


@app.post("/ingest")
def ingest(req: IngestRequest):
    """Загрузка нового документа/цитаты в граф."""
    try:
        embedding = get_embedding(req.text)
    except Exception as e:
        raise HTTPException(500, f"Embedding failed: {e}")

    if not embedding:
        raise HTTPException(500, "Empty embedding")

    quote_id = f"quote_ingested_{uuid.uuid4().hex[:12]}"
    year = None
    if req.date and len(req.date) >= 4:
        try:
            year = int(req.date[:4])
        except ValueError:
            pass

    # 1. В Qdrant
    qdrant.upsert(
        collection_name=COLLECTION,
        points=[PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "quote_id": quote_id,
                "text": req.text[:1000],
                "text_full": req.text,
                "date": req.date,
                "year": year,
                "period": "ingested",
                "cluster": None,
                "source_url": req.source_url,
                "source_domain": "",
                "event": req.event,
                "topic": "",
                "node_type": "Quote"
            }
        )]
    )

    # 2. В Neo4j
    with neo4j_driver.session() as session:
        session.run("""
            MERGE (q:Quote {node_id: $qid})
            SET q.text = $text, q.date = $date, q.year = $year,
                q.source_url = $url, q.event = $event, q.period = 'ingested'
        """, qid=quote_id, text=req.text[:5000], date=req.date, year=year,
            url=req.source_url, event=req.event)

        # Связываем с Фрадковым
        session.run("""
            MATCH (p:Person {name: 'Фрадков Михаил Ефимович'})
            MATCH (q:Quote {node_id: $qid})
            MERGE (p)-[:SAID]->(q)
        """, qid=quote_id)

    # 3. Находим семантически близкие цитаты
    similar = []
    results = qdrant.query_points(
        collection_name=COLLECTION,
        query=embedding,
        limit=10
    )
    for r in results.points:
        if r.payload.get("quote_id") != quote_id and r.score >= 0.75:
            similar.append({
                "quote_id": r.payload.get("quote_id"),
                "text": (r.payload.get("text", ""))[:200],
                "similarity": round(r.score, 4)
            })
            # Добавляем семантическую связь в Neo4j
            with neo4j_driver.session() as session:
                session.run("""
                    MATCH (a:Quote {node_id: $from_id})
                    MATCH (b:Quote {node_id: $to_id})
                    MERGE (a)-[r:SEMANTICALLY_RELATED]->(b)
                    SET r.similarity = $sim
                """, from_id=quote_id, to_id=r.payload.get("quote_id"), sim=round(r.score, 4))

    return {
        "status": "ok",
        "quote_id": quote_id,
        "embedding_dim": len(embedding),
        "similar_quotes_found": len(similar),
        "similar_quotes": similar[:5]
    }


@app.get("/stats", response_model=StatsResponse)
def stats():
    """Статистика графа."""
    qdrant_info = qdrant.get_collection(COLLECTION)

    with neo4j_driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        edge_count = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]

    timeline = _graph.get("metadata", {}).get("timeline", {})
    years = f"{timeline.get('start', '?')}-{timeline.get('end', '?')}" if timeline else "2000-2026"

    return StatsResponse(
        total_quotes=qdrant_info.points_count,
        total_entities=node_count,
        total_edges=edge_count,
        clusters=_stochastic.get("n_clusters", 20),
        years_covered=years,
        qdrant_points=qdrant_info.points_count,
        neo4j_nodes=node_count,
        neo4j_edges=edge_count
    )


@app.get("/clusters")
def list_clusters():
    """Список кластеров с примерами цитат."""
    clusters = defaultdict(list)

    # Берём примеры из Qdrant (scroll)
    offset = None
    all_points = []
    while True:
        results = qdrant.scroll(
            collection_name=COLLECTION,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        points, offset = results
        all_points.extend(points)
        if offset is None or len(points) < 100:
            break

    for p in all_points:
        cl = p.payload.get("cluster")
        if cl is not None:
            clusters[cl].append({
                "text": (p.payload.get("text", ""))[:150],
                "date": p.payload.get("date", "")
            })

    result = {}
    for cl_id in sorted(clusters.keys()):
        items = clusters[cl_id]
        result[cl_id] = {
            "count": len(items),
            "examples": items[:3]
        }

    return result


@app.get("/transitions")
def transitions():
    """Матрица переходов между кластерами."""
    return {
        "transition_matrix": _transition_matrix,
        "description": "Вероятности перехода между тематическими кластерами на основе семантических связей"
    }


if __name__ == "__main__":
    import uvicorn
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  Fradkov Ontology — Query API v1.0                         ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  POST /query      — стохастическое сопоставление           ║")
    print("║  POST /ingest     — загрузка нового документа              ║")
    print("║  GET  /stats      — статистика графа                       ║")
    print("║  GET  /clusters   — кластеры с примерами                   ║")
    print("║  GET  /transitions — матрица переходов                     ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║  http://localhost:8000/docs  — Swagger UI                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)

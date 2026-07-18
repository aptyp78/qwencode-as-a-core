#!/usr/bin/env python3
"""
Векторизация исторических цитат + семантические связи для всех цитат.
"""

import json
import numpy as np
import requests
from datetime import datetime


OLLAMA_API_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "qwen3-embedding:8b"
GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_phase2_merged.json"
OUTPUT_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_vectorized_full.json"


def get_embedding(text: str):
    try:
        resp = requests.post(OLLAMA_API_URL, json={"model": EMBEDDING_MODEL, "prompt": text}, timeout=60)
        resp.raise_for_status()
        return resp.json().get("embedding", [])
    except:
        return []


def cosine_similarity(v1, v2):
    a, b = np.array(v1), np.array(v2)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def main():
    print("=" * 60)
    print("Векторизация исторических цитат + семантические связи")
    print("=" * 60)
    print()
    
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    need_vectorize = [q for q in quotes if "embedding" not in q]
    
    print(f"Цитат всего: {len(quotes)}")
    print(f"Нужно векторизовать: {len(need_vectorize)}")
    print()
    
    # Векторизация
    print("Векторизация исторических цитат...")
    vectorized = 0
    for i, q in enumerate(need_vectorize, 1):
        text = q["attributes"].get("text", "")
        if text:
            emb = get_embedding(text)
            if emb:
                q["embedding"] = emb
                q["embedding_model"] = EMBEDDING_MODEL
                vectorized += 1
        if i % 100 == 0:
            print(f"  [{i}/{len(need_vectorize)}]")
    
    print(f"✓ Векторизовано: {vectorized}/{len(need_vectorize)}")
    print()
    
    # Семантические связи для ВСЕХ цитат
    print("Вычисление семантических связей для всех цитат...")
    quotes_with_emb = [q for q in quotes if "embedding" in q]
    print(f"Цитат с embedding: {len(quotes_with_emb)}")
    
    # Удаляем старые семантические связи
    graph["edges"] = [e for e in graph["edges"] if e["type"] != "semantically_related"]
    
    connections = []
    total = len(quotes_with_emb)
    
    for i in range(total):
        if i % 100 == 0:
            print(f"  [{i}/{total}]")
        
        for j in range(i + 1, total):
            sim = cosine_similarity(quotes_with_emb[i]["embedding"], quotes_with_emb[j]["embedding"])
            if sim >= 0.75:
                connections.append({
                    "from": quotes_with_emb[i]["id"],
                    "to": quotes_with_emb[j]["id"],
                    "type": "semantically_related",
                    "attributes": {"similarity": round(sim, 4)}
                })
    
    graph["edges"].extend(connections)
    
    print(f"✓ Семантических связей: {len(connections)}")
    print()
    
    # Сохраняем
    graph["metadata"]["vectorized_full"] = datetime.now().isoformat()
    graph["metadata"]["total_vectorized"] = len(quotes_with_emb)
    graph["metadata"]["total_semantic_connections"] = len(connections)
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print("=" * 60)
    print("Итог:")
    print("=" * 60)
    print(f"Узлов: {len(graph['nodes'])}")
    print(f"Рёбер: {len(graph['edges'])}")
    print(f"Цитат с embedding: {len(quotes_with_emb)}")
    print(f"Семантических связей: {len(connections)}")
    print()
    print(f"✓ Сохранено: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

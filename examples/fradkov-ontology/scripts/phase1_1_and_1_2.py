#!/usr/bin/env python3
"""
Фаза 1: Устранение критических разрывов.
С промежуточным сохранением после каждой подфазы.
"""

import json
import numpy as np
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict


OLLAMA_API_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "qwen3-embedding:8b"
GRAPH_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_final_real.json"
PHASE1_1_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_phase1_1.json"
PHASE1_2_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_phase1_2.json"


def get_embedding(text: str) -> List[float]:
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("embedding", [])
    except:
        return []


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    a, b = np.array(v1), np.array(v2)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def phase1_1_vectorize():
    """Фаза 1.1: Векторизация."""
    print("=" * 60)
    print("Фаза 1.1: Векторизация всех цитат")
    print("=" * 60)
    
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    print(f"Цитат: {len(quotes)}")
    
    done = 0
    for i, q in enumerate(quotes, 1):
        text = q["attributes"].get("text", "")
        if text:
            emb = get_embedding(text)
            if emb:
                q["embedding"] = emb
                done += 1
        if i % 50 == 0:
            print(f"  [{i}/{len(quotes)}]")
    
    with open(PHASE1_1_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False)
    
    print(f"✓ Векторизовано: {done}/{len(quotes)}")
    print(f"✓ Сохранено: {PHASE1_1_PATH}")
    return graph


def phase1_2_semantic_connections():
    """Фаза 1.2: Семантические связи."""
    print()
    print("=" * 60)
    print("Фаза 1.2: Семантические связи")
    print("=" * 60)
    
    with open(PHASE1_1_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote" and "embedding" in n]
    print(f"Цитат с embedding: {len(quotes)}")
    
    connections = []
    for i in range(len(quotes)):
        if i % 50 == 0:
            print(f"  [{i}/{len(quotes)}]")
        
        for j in range(i + 1, len(quotes)):
            sim = cosine_similarity(quotes[i]["embedding"], quotes[j]["embedding"])
            if sim >= 0.75:
                connections.append({
                    "from": quotes[i]["id"],
                    "to": quotes[j]["id"],
                    "type": "semantically_related",
                    "attributes": {"similarity": round(sim, 4)}
                })
    
    graph["edges"].extend(connections)
    
    with open(PHASE1_2_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False)
    
    print(f"✓ Семантических связей: {len(connections)}")
    print(f"✓ Сохранено: {PHASE1_2_PATH}")
    return graph


if __name__ == "__main__":
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "  ФАЗА 1: ВЕКТОРИЗАЦИЯ + СЕМАНТИЧЕСКИЕ СВЯЗИ".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    phase1_1_vectorize()
    phase1_2_semantic_connections()
    
    print()
    print("✓ Фазы 1.1-1.2 завершены")

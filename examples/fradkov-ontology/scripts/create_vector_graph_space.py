#!/usr/bin/env python3
"""
Создание вычислительного векторно-графового пространства.
Векторизация высказываний, вычисление сходства, создание семантических связей.
"""

import json
import numpy as np
import requests
from pathlib import Path
from datetime import datetime


OLLAMA_API_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "qwen3-embedding:8b"


def get_embedding(text: str) -> list[float]:
    """Получает embedding для текста."""
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("embedding", [])
    except Exception as e:
        return []


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Вычисляет косинусное сходство."""
    a = np.array(v1)
    b = np.array(v2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def vectorize_quotes(quotes: list[dict]) -> list[dict]:
    """Векторизует все высказывания."""
    
    print("Векторизация высказываний...")
    vectorized = []
    total = len(quotes)
    
    for i, quote in enumerate(quotes, 1):
        if i % 50 == 0:
            print(f"  [{i}/{total}]...")
        
        text = quote["text"]
        embedding = get_embedding(text)
        
        if embedding:
            quote_with_vector = {
                **quote,
                "embedding": embedding,
                "embedding_model": EMBEDDING_MODEL
            }
            vectorized.append(quote_with_vector)
    
    print(f"  ✓ Векторизовано: {len(vectorized)}/{total}")
    return vectorized


def compute_semantic_connections(quotes: list[dict], threshold: float = 0.75, max_connections: int = 5) -> list[dict]:
    """Вычисляет семантические связи между высказываниями."""
    
    print("\nВычисление семантических связей...")
    connections = []
    total = len(quotes)
    
    for i in range(total):
        if i % 50 == 0:
            print(f"  [{i}/{total}]...")
        
        quote1 = quotes[i]
        if "embedding" not in quote1:
            continue
        
        # Находим похожие цитаты
        similarities = []
        for j in range(total):
            if i == j:
                continue
            
            quote2 = quotes[j]
            if "embedding" not in quote2:
                continue
            
            similarity = cosine_similarity(quote1["embedding"], quote2["embedding"])
            
            if similarity >= threshold:
                similarities.append({
                    "from": quote1["id"],
                    "to": quote2["id"],
                    "similarity": similarity,
                    "type": "semantically_related"
                })
        
        # Сортируем по сходству и берём топ-N
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        connections.extend(similarities[:max_connections])
    
    print(f"  ✓ Создано связей: {len(connections)}")
    return connections


def create_vector_graph_space(quotes: list[dict], connections: list[dict], output_path: str):
    """Создаёт векторно-графовое пространство."""
    
    print("\nСоздание векторно-графового пространства...")
    
    # Строим граф
    graph = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "type": "vector_graph_space",
            "description": "Вычислительное векторно-графовое пространство высказываний",
            "total_quotes": len(quotes),
            "total_connections": len(connections),
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dimensions": len(quotes[0]["embedding"]) if quotes else 0,
            "similarity_threshold": 0.75
        },
        "nodes": [],
        "edges": []
    }
    
    # Добавляем цитаты как узлы
    for quote in quotes:
        node = {
            "id": quote["id"],
            "type": "Quote",
            "name": quote["text"][:100] + "..." if len(quote["text"]) > 100 else quote["text"],
            "attributes": {
                "text": quote["text"],
                "date": quote["date"],
                "topic": quote["topic"],
                "event": quote["event"]
            },
            "embedding": quote.get("embedding", [])
        }
        graph["nodes"].append(node)
    
    # Добавляем семантические связи
    for conn in connections:
        edge = {
            "from": conn["from"],
            "to": conn["to"],
            "type": conn["type"],
            "attributes": {
                "similarity": conn["similarity"]
            }
        }
        graph["edges"].append(edge)
    
    # Сохраняем
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ Векторно-графовое пространство сохранено в {output_path}")
    
    # Статистика
    print("\nСтатистика:")
    print(f"  Узлов (цитат): {len(graph['nodes'])}")
    print(f"  Рёбер (семантических связей): {len(graph['edges'])}")
    print(f"  Размерность embeddings: {graph['metadata']['embedding_dimensions']}")
    print(f"  Порог сходства: {graph['metadata']['similarity_threshold']}")
    
    # Средняя степень связности
    if graph["nodes"]:
        avg_degree = len(graph["edges"]) * 2 / len(graph["nodes"])
        print(f"  Средняя степень связности: {avg_degree:.2f}")
    
    return graph


if __name__ == "__main__":
    print("=" * 60)
    print("Создание вычислительного векторно-графового пространства")
    print("=" * 60)
    print()
    
    # Загружаем высказывания
    quotes_path = "/Users/arturoceretnyj/fradkov-ontology/data/fradkov_quotes_extended.json"
    with open(quotes_path, "r", encoding="utf-8") as f:
        quotes_db = json.load(f)
    
    quotes = quotes_db["quotes"]
    print(f"Загружено высказываний: {len(quotes)}")
    print()
    
    # Векторизуем
    vectorized_quotes = vectorize_quotes(quotes)
    
    # Вычисляем семантические связи
    connections = compute_semantic_connections(vectorized_quotes, threshold=0.75, max_connections=5)
    
    # Создаём векторно-графовое пространство
    output_path = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_vector_graph_space.json"
    vector_graph_space = create_vector_graph_space(vectorized_quotes, connections, output_path)
    
    print()
    print("=" * 60)
    print("✓ Векторно-графовое пространство создано")
    print("=" * 60)
    print()
    print("Что это даёт:")
    print("  • Семантические связи между цитатами (по смыслу)")
    print("  • Возможность кластеризации (группировки по темам)")
    print("  • Поиск по сходству (найти похожие высказывания)")
    print("  • Анализ тематических кластеров")
    print("  • Визуализация как векторное пространство (t-SNE/UMAP)")

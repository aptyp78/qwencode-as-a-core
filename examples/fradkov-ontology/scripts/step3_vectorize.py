#!/usr/bin/env python3
"""
Шаг 3: Векторизация сущностей онтологического графа.
Использует qwen3-embedding:8b через Ollama API.
"""

import json
import requests
from pathlib import Path
from datetime import datetime


OLLAMA_API_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "qwen3-embedding:8b"


def get_embedding(text: str) -> list[float]:
    """Получает embedding для текста через Ollama API."""
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": EMBEDDING_MODEL,
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get("embedding", [])
    except Exception as e:
        print(f"  ⚠ Ошибка при получении embedding для '{text[:50]}...': {e}")
        return []


def create_text_representation(node: dict) -> str:
    """Создаёт текстовое представление узла для векторизации."""
    parts = [node["name"]]
    
    if "attributes" in node:
        for key, value in node["attributes"].items():
            if isinstance(value, str) and value:
                parts.append(f"{key}: {value}")
            elif isinstance(value, list) and value:
                parts.append(f"{key}: {', '.join(str(v) for v in value)}")
    
    return " | ".join(parts)


def vectorize_graph(graph_path: str, output_path: str):
    """Векторизует все узлы графа."""
    
    # Загружаем граф
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    print(f"Загружен граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    print()
    
    # Векторизуем узлы
    vectorized_nodes = []
    total = len(graph["nodes"])
    
    for i, node in enumerate(graph["nodes"], 1):
        text = create_text_representation(node)
        print(f"[{i}/{total}] Векторизация: {node['type']} - {node['name'][:50]}...")
        
        embedding = get_embedding(text)
        
        if embedding:
            vectorized_node = {
                **node,
                "embedding": embedding,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_date": datetime.now().isoformat(),
                "text_representation": text
            }
            vectorized_nodes.append(vectorized_node)
            print(f"  ✓ Embedding получен ({len(embedding)} dimensions)")
        else:
            print(f"  ✗ Embedding не получен")
    
    # Сохраняем векторизованный граф
    vectorized_graph = {
        "metadata": {
            **graph["metadata"],
            "vectorized_date": datetime.now().isoformat(),
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dimensions": len(vectorized_nodes[0]["embedding"]) if vectorized_nodes else 0,
            "total_vectorized": len(vectorized_nodes)
        },
        "nodes": vectorized_nodes,
        "edges": graph["edges"]
    }
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(vectorized_graph, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"✓ Векторизованный граф сохранён в {output_path}")
    print(f"  Векторизовано узлов: {len(vectorized_nodes)}/{total}")
    
    return vectorized_graph


if __name__ == "__main__":
    print("=" * 60)
    print("Шаг 3: Векторизация сущностей")
    print("=" * 60)
    print()
    print(f"Модель: {EMBEDDING_MODEL}")
    print(f"API: {OLLAMA_API_URL}")
    print()
    
    # Проверяем доступность Ollama
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        print("✓ Ollama API доступен")
        print()
    except Exception as e:
        print(f"✗ Ошибка подключения к Ollama: {e}")
        print("  Убедитесь, что Ollama запущен: ollama serve")
        exit(1)
    
    # Векторизуем граф
    graph_path = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_graph.json"
    output_path = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_vectorized.json"
    
    vectorized_graph = vectorize_graph(graph_path, output_path)
    
    print()
    print("✓ Шаг 3 завершён")
    print()
    print("Следующий шаг: Загрузка в граф (Neo4j)")

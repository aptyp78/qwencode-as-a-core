#!/usr/bin/env python3
"""
Шаг 5: Вычисления на онтологическом графе.
Семантический поиск, структурный поиск, анализ связей.
"""

import json
import numpy as np
import requests
from pathlib import Path


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
        print(f"Ошибка: {e}")
        return []


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Вычисляет косинусное сходство между двумя векторами."""
    a = np.array(v1)
    b = np.array(v2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def load_vectorized_graph(graph_path: str) -> dict:
    """Загружает векторизованный граф."""
    with open(graph_path, "r", encoding="utf-8") as f:
        return json.load(f)


def semantic_search(graph: dict, query: str, top_k: int = 5) -> list[dict]:
    """Семантический поиск: находит узлы, наиболее похожие на запрос."""
    print(f"\n🔍 Семантический поиск: '{query}'")
    print("-" * 60)
    
    # Получаем embedding запроса
    query_embedding = get_embedding(query)
    if not query_embedding:
        print("Не удалось получить embedding для запроса")
        return []
    
    # Вычисляем сходство со всеми узлами
    results = []
    for node in graph["nodes"]:
        if "embedding" in node and node["embedding"]:
            similarity = cosine_similarity(query_embedding, node["embedding"])
            results.append({
                "node": node,
                "similarity": similarity
            })
    
    # Сортируем по сходству
    results.sort(key=lambda x: x["similarity"], reverse=True)
    
    # Выводим результаты
    for i, result in enumerate(results[:top_k], 1):
        node = result["node"]
        print(f"\n{i}. [{node['type']}] {node['name']}")
        print(f"   Сходство: {result['similarity']:.4f}")
        if "attributes" in node:
            for key, value in list(node["attributes"].items())[:3]:
                print(f"   {key}: {value}")
    
    return results[:top_k]


def structural_search(graph: dict, node_type: str, filter_value: str = None) -> list[dict]:
    """Структурный поиск: находит узлы по типу и атрибутам."""
    print(f"\n🔍 Структурный поиск: тип={node_type}")
    if filter_value:
        print(f"   фильтр: {filter_value}")
    print("-" * 60)
    
    results = []
    for node in graph["nodes"]:
        if node["type"] == node_type:
            if filter_value:
                # Проверяем, есть ли filter_value в имени или атрибутах
                if filter_value.lower() in node["name"].lower():
                    results.append(node)
                    print(f"\n• {node['name']}")
                    if "attributes" in node:
                        for key, value in list(node["attributes"].items())[:3]:
                            print(f"  {key}: {value}")
            else:
                results.append(node)
                print(f"\n• {node['name']}")
                if "attributes" in node:
                    for key, value in list(node["attributes"].items())[:3]:
                        print(f"  {key}: {value}")
    
    print(f"\nНайдено: {len(results)}")
    return results


def analyze_connections(graph: dict, node_id: str) -> dict:
    """Анализ связей: находит все связи узла."""
    print(f"\n🔗 Анализ связей для: {node_id}")
    print("-" * 60)
    
    # Находим узел
    target_node = None
    for node in graph["nodes"]:
        if node["id"] == node_id:
            target_node = node
            break
    
    if not target_node:
        print(f"Узел {node_id} не найден")
        return {}
    
    print(f"\nУзел: [{target_node['type']}] {target_node['name']}")
    
    # Находим исходящие связи
    outgoing = []
    for edge in graph["edges"]:
        if edge["from"] == node_id:
            # Находим целевой узел
            target = next((n for n in graph["nodes"] if n["id"] == edge["to"]), None)
            if target:
                outgoing.append({
                    "edge": edge,
                    "target": target
                })
    
    # Находим входящие связи
    incoming = []
    for edge in graph["edges"]:
        if edge["to"] == node_id:
            # Находим исходный узел
            source = next((n for n in graph["nodes"] if n["id"] == edge["from"]), None)
            if source:
                incoming.append({
                    "edge": edge,
                    "source": source
                })
    
    # Выводим результаты
    if outgoing:
        print(f"\nИсходящие связи ({len(outgoing)}):")
        for conn in outgoing:
            edge = conn["edge"]
            target = conn["target"]
            print(f"  → [{edge['type']}] → {target['name']}")
    
    if incoming:
        print(f"\nВходящие связи ({len(incoming)}):")
        for conn in incoming:
            edge = conn["edge"]
            source = conn["source"]
            print(f"  ← [{edge['type']}] ← {source['name']}")
    
    return {
        "node": target_node,
        "outgoing": outgoing,
        "incoming": incoming
    }


def find_path(graph: dict, from_id: str, to_id: str, max_depth: int = 3) -> list:
    """Поиск пути между двумя узлами."""
    print(f"\n🛤️  Поиск пути: {from_id} → {to_id}")
    print("-" * 60)
    
    # Простой BFS
    from collections import deque
    
    queue = deque([(from_id, [from_id])])
    visited = {from_id}
    
    while queue:
        current_id, path = queue.popleft()
        
        if current_id == to_id:
            print(f"\nПуть найден (длина: {len(path) - 1}):")
            for i, node_id in enumerate(path):
                node = next((n for n in graph["nodes"] if n["id"] == node_id), None)
                if node:
                    prefix = "  " * i
                    print(f"{prefix}→ [{node['type']}] {node['name']}")
            return path
        
        if len(path) > max_depth:
            continue
        
        # Находим соседей
        for edge in graph["edges"]:
            if edge["from"] == current_id:
                neighbor_id = edge["to"]
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
            elif edge["to"] == current_id:
                neighbor_id = edge["from"]
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
    
    print("\nПуть не найден")
    return []


def run_experiments(graph: dict):
    """Запускает серию экспериментов."""
    
    print("\n" + "=" * 60)
    print("ЭКСПЕРИМЕНТЫ С ВЫЧИСЛЕНИЯМИ")
    print("=" * 60)
    
    # Эксперимент 1: Семантический поиск
    print("\n" + "=" * 60)
    print("Эксперимент 1: Семантический поиск")
    print("=" * 60)
    
    queries = [
        "деятельность в области экспорта",
        "банковское дело и оборонно-промышленный комплекс",
        "спорт и общественная деятельность",
        "научные публикации"
    ]
    
    for query in queries:
        semantic_search(graph, query, top_k=3)
    
    # Эксперимент 2: Структурный поиск
    print("\n" + "=" * 60)
    print("Эксперимент 2: Структурный поиск")
    print("=" * 60)
    
    structural_search(graph, "Organization")
    structural_search(graph, "Activity")
    structural_search(graph, "Project")
    
    # Эксперимент 3: Анализ связей
    print("\n" + "=" * 60)
    print("Эксперимент 3: Анализ связей")
    print("=" * 60)
    
    analyze_connections(graph, "person_fradkov_pm")
    analyze_connections(graph, "org_пао_«промсвязьбанк»")
    
    # Эксперимент 4: Поиск пути
    print("\n" + "=" * 60)
    print("Эксперимент 4: Поиск пути")
    print("=" * 60)
    
    find_path(graph, "person_fradkov_pm", "project_2", max_depth=3)


if __name__ == "__main__":
    print("=" * 60)
    print("Шаг 5: Вычисления на онтологическом графе")
    print("=" * 60)
    
    # Загружаем векторизованный граф
    graph_path = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_vectorized.json"
    graph = load_vectorized_graph(graph_path)
    
    print(f"Загружен граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    
    # Запускаем эксперименты
    run_experiments(graph)
    
    print("\n" + "=" * 60)
    print("✓ Шаг 5 завершён")
    print("=" * 60)
    print("\nСледующий шаг: Интерфейс (CLI для запросов)")

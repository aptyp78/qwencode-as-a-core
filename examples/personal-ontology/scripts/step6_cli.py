#!/usr/bin/env python3
"""
Шаг 6: Интерфейс (CLI для запросов к онтологическому графу).
Интерактивный интерфейс для работы с цифровой тенью Фрадкова П.М.
"""

import json
import sys
import numpy as np
import requests
from pathlib import Path


OLLAMA_API_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "qwen3-embedding:8b"
GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_vectorized.json"


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


def load_graph() -> dict:
    """Загружает векторизованный граф."""
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def semantic_search(graph: dict, query: str, top_k: int = 5) -> list[dict]:
    """Семантический поиск."""
    query_embedding = get_embedding(query)
    if not query_embedding:
        return []
    
    results = []
    for node in graph["nodes"]:
        if "embedding" in node and node["embedding"]:
            similarity = cosine_similarity(query_embedding, node["embedding"])
            results.append({"node": node, "similarity": similarity})
    
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


def structural_search(graph: dict, node_type: str) -> list[dict]:
    """Структурный поиск по типу."""
    return [node for node in graph["nodes"] if node["type"] == node_type]


def analyze_connections(graph: dict, node_id: str) -> dict:
    """Анализ связей узла."""
    outgoing = []
    incoming = []
    
    for edge in graph["edges"]:
        if edge["from"] == node_id:
            target = next((n for n in graph["nodes"] if n["id"] == edge["to"]), None)
            if target:
                outgoing.append({"edge": edge, "target": target})
        elif edge["to"] == node_id:
            source = next((n for n in graph["nodes"] if n["id"] == edge["from"]), None)
            if source:
                incoming.append({"edge": edge, "source": source})
    
    return {"outgoing": outgoing, "incoming": incoming}


def process_query(graph: dict, query: str):
    """Обрабатывает запрос пользователя."""
    query_lower = query.lower()
    
    # Определяем тип запроса
    if "кто" in query_lower or "что" in query_lower or "расскажи" in query_lower:
        # Семантический поиск
        print(f"\n🔍 Поиск по запросу: '{query}'\n")
        results = semantic_search(graph, query, top_k=5)
        
        if results:
            for i, result in enumerate(results, 1):
                node = result["node"]
                print(f"{i}. [{node['type']}] {node['name']}")
                print(f"   Сходство: {result['similarity']:.4f}")
                if "attributes" in node:
                    for key, value in list(node["attributes"].items())[:3]:
                        if isinstance(value, str) and len(value) < 100:
                            print(f"   {key}: {value}")
                print()
        else:
            print("Ничего не найдено")
    
    elif "организации" in query_lower or "где работал" in query_lower:
        # Структурный поиск: организации
        print("\n🏢 Организации:\n")
        orgs = structural_search(graph, "Organization")
        for org in orgs:
            print(f"• {org['name']}")
            if "attributes" in org and "industry" in org["attributes"]:
                print(f"  Отрасль: {org['attributes']['industry']}")
        print(f"\nВсего: {len(orgs)}")
    
    elif "виды деятельности" in query_lower or "чем занимался" in query_lower:
        # Структурный поиск: виды деятельности
        print("\n📋 Виды деятельности:\n")
        activities = structural_search(graph, "Activity")
        for activity in activities:
            print(f"• {activity['name']}")
        print(f"\nВсего: {len(activities)}")
    
    elif "проекты" in query_lower:
        # Структурный поиск: проекты
        print("\n🚀 Проекты:\n")
        projects = structural_search(graph, "Project")
        for project in projects:
            print(f"• {project['name']}")
            if "attributes" in project and "status" in project["attributes"]:
                print(f"  Статус: {project['attributes']['status']}")
        print(f"\nВсего: {len(projects)}")
    
    elif "связи" in query_lower or "контакты" in query_lower:
        # Анализ связей главной персоны
        print("\n🔗 Связи Фрадкова П.М.:\n")
        connections = analyze_connections(graph, "person_fradkov_pm")
        
        print(f"Исходящие связи: {len(connections['outgoing'])}")
        for conn in connections["outgoing"][:10]:
            edge = conn["edge"]
            target = conn["target"]
            print(f"  → [{edge['type']}] {target['name']}")
        
        if len(connections["outgoing"]) > 10:
            print(f"  ... и ещё {len(connections['outgoing']) - 10}")
    
    elif "помощь" in query_lower or "help" in query_lower:
        print("\n📖 Доступные команды:\n")
        print("• 'кто такой ...' / 'расскажи о ...' — семантический поиск")
        print("• 'организации' / 'где работал' — список организаций")
        print("• 'виды деятельности' / 'чем занимался' — список видов деятельности")
        print("• 'проекты' — список проектов")
        print("• 'связи' / 'контакты' — анализ связей")
        print("• 'помощь' / 'help' — эта справка")
        print("• 'выход' / 'exit' / 'quit' — выход")
    
    elif "выход" in query_lower or "exit" in query_lower or "quit" in query_lower:
        print("\nДо свидания!")
        sys.exit(0)
    
    else:
        # По умолчанию — семантический поиск
        print(f"\n🔍 Поиск по запросу: '{query}'\n")
        results = semantic_search(graph, query, top_k=5)
        
        if results:
            for i, result in enumerate(results, 1):
                node = result["node"]
                print(f"{i}. [{node['type']}] {node['name']}")
                print(f"   Сходство: {result['similarity']:.4f}")
                if "attributes" in node:
                    for key, value in list(node["attributes"].items())[:2]:
                        if isinstance(value, str) and len(value) < 100:
                            print(f"   {key}: {value}")
                print()
        else:
            print("Ничего не найдено. Попробуйте 'помощь' для списка команд.")


def main():
    """Главная функция CLI."""
    print("=" * 60)
    print("Онтологический граф Фрадкова П.М.")
    print("Цифровая тень личности")
    print("=" * 60)
    print()
    
    # Загружаем граф
    try:
        graph = load_graph()
        print(f"✓ Загружен граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
        print()
    except Exception as e:
        print(f"✗ Ошибка загрузки графа: {e}")
        print(f"  Убедитесь, что файл существует: {GRAPH_PATH}")
        sys.exit(1)
    
    print("Введите запрос (или 'помощь' для списка команд):")
    print()
    
    # Интерактивный цикл
    while True:
        try:
            query = input("> ").strip()
            
            if not query:
                continue
            
            process_query(graph, query)
            print()
        
        except KeyboardInterrupt:
            print("\n\nДо свидания!")
            break
        except EOFError:
            print("\n\nДо свидания!")
            break
        except Exception as e:
            print(f"\n✗ Ошибка: {e}")
            print()


if __name__ == "__main__":
    main()

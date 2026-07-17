#!/usr/bin/env python3
"""
Очистка графа от синтетических данных.
Оставляет только реальные высказывания и сущности.
"""

import json
from pathlib import Path


def clean_graph_from_synthetic_data():
    """Удаляет синтетические данные из графа."""
    
    print("=" * 60)
    print("Очистка графа от синтетических данных")
    print("=" * 60)
    print()
    
    # Загружаем финальный граф
    graph_path = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_final.json"
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    print(f"Исходный граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    
    # Загружаем базу цитат
    quotes_path = "/Users/arturoceretnyj/fradkov-ontology/data/fradkov_quotes.json"
    with open(quotes_path, "r", encoding="utf-8") as f:
        quotes_db = json.load(f)
    
    real_quote_ids = set(q["id"] for q in quotes_db["quotes"])
    print(f"Реальных цитат: {len(real_quote_ids)}")
    print()
    
    # Фильтруем узлы
    print("Фильтрация узлов...")
    original_nodes = len(graph["nodes"])
    
    filtered_nodes = []
    removed_quotes = 0
    
    for node in graph["nodes"]:
        if node["type"] == "Quote":
            # Оставляем только реальные цитаты
            if node["id"] in real_quote_ids:
                filtered_nodes.append(node)
            else:
                removed_quotes += 1
        else:
            # Все не-цитатные узлы оставляем
            filtered_nodes.append(node)
    
    print(f"  Удалено синтетических цитат: {removed_quotes}")
    print(f"  Осталось узлов: {len(filtered_nodes)}")
    print()
    
    # Фильтруем рёбра
    print("Фильтрация рёбер...")
    original_edges = len(graph["edges"])
    
    # Создаём множество ID оставшихся узлов
    remaining_node_ids = set(node["id"] for node in filtered_nodes)
    
    filtered_edges = []
    removed_edges = 0
    
    for edge in graph["edges"]:
        # Оставляем только рёбра между оставшимися узлами
        if edge["from"] in remaining_node_ids and edge["to"] in remaining_node_ids:
            filtered_edges.append(edge)
        else:
            removed_edges += 1
    
    print(f"  Удалено рёбер: {removed_edges}")
    print(f"  Осталось рёбер: {len(filtered_edges)}")
    print()
    
    # Создаём очищенный граф
    cleaned_graph = {
        "metadata": {
            **graph["metadata"],
            "cleaned_date": "2026-07-15",
            "synthetic_data_removed": True,
            "real_quotes_only": True,
            "purpose": "Стохастическое сопоставление при поступлении документов"
        },
        "nodes": filtered_nodes,
        "edges": filtered_edges
    }
    
    # Обновляем статистику цитат
    if "quotes" in cleaned_graph["metadata"]:
        cleaned_graph["metadata"]["quotes"] = {
            "total_quotes": len(real_quote_ids),
            "quote_types": {
                "real": len(real_quote_ids),
                "synthetic": 0
            }
        }
    
    # Сохраняем
    output_path = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_clean.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cleaned_graph, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Очищенный граф сохранён в {output_path}")
    print()
    
    # Статистика
    print("=" * 60)
    print("Финальная статистика:")
    print("=" * 60)
    print(f"Узлов: {len(cleaned_graph['nodes'])}")
    print(f"Рёбер: {len(cleaned_graph['edges'])}")
    print()
    
    # Подсчёт по типам
    node_types = {}
    for node in cleaned_graph["nodes"]:
        node_type = node["type"]
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    print("Узлы по типам:")
    for node_type, count in sorted(node_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {node_type}: {count}")
    
    print()
    print("=" * 60)
    print("✓ Очистка завершена")
    print("=" * 60)
    
    return cleaned_graph


if __name__ == "__main__":
    clean_graph_from_synthetic_data()

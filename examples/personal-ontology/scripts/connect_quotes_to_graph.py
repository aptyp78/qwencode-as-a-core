#!/usr/bin/env python3
"""
Соединение расширенной базы высказываний с графом.
Создаёт финальную версию онтологического графа с цитатами.
"""

import json
from datetime import datetime
from pathlib import Path


def connect_extended_quotes_to_graph():
    """Соединяет расширенную базу высказываний с графом."""
    
    print("=" * 60)
    print("Соединение высказываний с графом")
    print("=" * 60)
    print()
    
    # Загружаем граф
    graph_path = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_enriched.json"
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    print(f"Загружен граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    
    # Загружаем расширенную базу высказываний
    quotes_path = "/Users/arturoceretnyj/personal-ontology/data/personal_quotes_extended.json"
    with open(quotes_path, "r", encoding="utf-8") as f:
        quotes_db = json.load(f)
    
    print(f"Загружена база высказываний: {len(quotes_db['quotes'])} цитат")
    print()
    
    # Добавляем высказывания как узлы
    print("Добавление высказываний в граф...")
    for quote in quotes_db["quotes"]:
        quote_id = quote["id"]
        
        # Проверяем, нет ли уже такого узла
        if any(node["id"] == quote_id for node in graph["nodes"]):
            continue
        
        # Создаём узел для высказывания
        node = {
            "id": quote_id,
            "type": "Quote",
            "name": quote["text"][:100] + "..." if len(quote["text"]) > 100 else quote["text"],
            "attributes": {
                "text": quote["text"],
                "date": quote["date"],
                "event": quote["event"],
                "topic": quote["topic"],
                "source": quote["source"],
                "significance": quote.get("significance", "")
            }
        }
        
        if "url" in quote:
            node["attributes"]["url"] = quote["url"]
        
        graph["nodes"].append(node)
        
        # Связь с Фрадковым
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": quote_id,
            "type": "said",
            "attributes": {
                "date": quote["date"],
                "context": quote["event"]
            }
        })
    
    # Обновляем метаданные
    graph["metadata"]["quotes"] = {
        "total_quotes": len(quotes_db["quotes"]),
        "quote_types": {
            "real": 25,
            "synthetic": len(quotes_db["quotes"]) - 25
        },
        "topics_count": len(set(q["topic"] for q in quotes_db["quotes"])),
        "date_range": {
            "start": min(q["date"] for q in quotes_db["quotes"]),
            "end": max(q["date"] for q in quotes_db["quotes"])
        }
    }
    
    # Сохраняем финальный граф
    output_path = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_final.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Финальный граф сохранён в {output_path}")
    print()
    
    # Статистика
    print("=" * 60)
    print("Финальная статистика графа:")
    print("=" * 60)
    print(f"Всего узлов: {len(graph['nodes'])}")
    print(f"Всего рёбер: {len(graph['edges'])}")
    print()
    
    # Подсчёт по типам узлов
    node_types = {}
    for node in graph["nodes"]:
        node_type = node["type"]
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    print("Узлы по типам:")
    for node_type, count in sorted(node_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {node_type}: {count}")
    
    print()
    
    # Подсчёт по типам рёбер
    edge_types = {}
    for edge in graph["edges"]:
        edge_type = edge["type"]
        edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
    
    print("Рёбра по типам:")
    for edge_type, count in sorted(edge_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {edge_type}: {count}")
    
    print()
    print("=" * 60)
    print("✓ Соединение завершено")
    print("=" * 60)
    
    return graph


def create_final_summary(graph: dict):
    """Создаёт финальное описание графа."""
    
    summary = f"""
═══════════════════════════════════════════════════════════════
ФИНАЛЬНАЯ ЦИФРОВАЯ ТЕНЬ ФРАДКОВА П.М.
Онтологический векторно-вычислительный граф личности
═══════════════════════════════════════════════════════════════

ДАТА СОЗДАНИЯ: {datetime.now().strftime('%Y-%m-%d')}

СТРУКТУРА ГРАФА:

• Узлов: {len(graph['nodes'])}
• Рёбер: {len(graph['edges'])}

ТИПЫ УЗЛОВ:
"""
    
    # Подсчёт по типам
    node_types = {}
    for node in graph["nodes"]:
        node_type = node["type"]
        node_types[node_type] = node_types.get(node_type, 0) + 1
    
    for node_type, count in sorted(node_types.items(), key=lambda x: x[1], reverse=True):
        summary += f"• {node_type}: {count}\n"
    
    summary += f"""
ВЫСКАЗЫВАНИЯ:

• Всего цитат: {graph['metadata']['quotes']['total_quotes']}
• Реальных: {graph['metadata']['quotes']['quote_types']['real']}
• Синтетических: {graph['metadata']['quotes']['quote_types']['synthetic']}
• Тем: {graph['metadata']['quotes']['topics_count']}
• Период: {graph['metadata']['quotes']['date_range']['start']} — {graph['metadata']['quotes']['date_range']['end']}

ИСТОЧНИКИ ДАННЫХ:

• Википедия (биография)
• Яндекс-поиск (новости, интервью)
• Официальные сайты (ПСБ, ВФЛА, ВШЭ)
• Научные публикации
• Синтетические данные (на основе реальных тем)

ВРЕМЕННАЯ ШКАЛА:

• Период: 2000-2026
• Событий: {len([n for n in graph['nodes'] if n['type'] == 'TimelineEvent'])}
• Карьерных позиций: 11
• Видов деятельности: 10+

ТЕХНОЛОГИИ:

• Язык: Python 3
• Хранилище: JSON (граф + векторы)
• Embeddings: qwen3-embedding:8b (4096d)
• Визуализация: Pyvis (интерактивный HTML)
• Вычисления: семантический поиск, структурный поиск, анализ связей

ФАЙЛЫ:

• output/personal_ontology_final.json — финальный граф
• output/personal_ontology_vectorized.json — векторизованный граф
• output/fradkov_graph_visualization.html — визуализация
• data/personal_quotes_extended.json — база высказываний (525 цитат)
• data/fradkov_biography.json — биография из Википедии
• data/fradkov_additional_sources.json — дополнительные источники

═══════════════════════════════════════════════════════════════
"""
    
    return summary


if __name__ == "__main__":
    # Соединяем высказывания с графом
    final_graph = connect_extended_quotes_to_graph()
    
    print()
    
    # Создаём финальное описание
    summary = create_final_summary(final_graph)
    print(summary)
    
    # Сохраняем описание
    summary_path = "/Users/arturoceretnyj/personal-ontology/output/FINAL_SUMMARY.md"
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(f"✓ Финальное описание сохранено в {summary_path}")

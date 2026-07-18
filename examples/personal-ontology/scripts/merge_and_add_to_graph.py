#!/usr/bin/env python3
"""
Объединение всех реальных высказываний и добавление в граф.
Финальная версия онтологического графа с реальными цитатами.
"""

import json
from datetime import datetime
from pathlib import Path


def merge_all_real_quotes():
    """Объединяет все реальные высказывания."""
    
    print("=" * 60)
    print("Объединение всех реальных высказываний")
    print("=" * 60)
    print()
    
    # Загружаем все источники
    sources = [
        "/Users/arturoceretnyj/personal-ontology/data/fradkov_massive_parsed_quotes.json",
        "/Users/arturoceretnyj/personal-ontology/data/fradkov_real_quotes_final.json",
        "/Users/arturoceretnyj/personal-ontology/data/personal_quotes.json"
    ]
    
    all_quotes = []
    
    for source_path in sources:
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                quotes = data.get("quotes", [])
                print(f"Загружено из {source_path.split('/')[-1]}: {len(quotes)} цитат")
                all_quotes.extend(quotes)
        except Exception as e:
            print(f"⚠ Ошибка загрузки {source_path}: {e}")
    
    print()
    
    # Фильтруем только реальные
    real_quotes = [q for q in all_quotes if q.get("type") == "real"]
    print(f"Реальных высказываний: {len(real_quotes)}")
    
    # Убираем дубликаты
    unique_quotes = []
    seen_texts = set()
    
    for quote in real_quotes:
        text = quote.get("text", "").strip()
        if text and len(text) > 20:
            text_normalized = text.lower()
            if text_normalized not in seen_texts:
                seen_texts.add(text_normalized)
                unique_quotes.append(quote)
    
    print(f"Уникальных реальных высказываний: {len(unique_quotes)}")
    print()
    
    # Сохраняем объединённую базу
    merged_db = {
        "metadata": {
            "subject": "Фрадков Пётр Михайлович",
            "created": datetime.now().isoformat(),
            "total_quotes": len(unique_quotes),
            "type": "real_quotes_merged",
            "sources": [
                "Масштабный парсинг (108 страниц)",
                "Ручной сбор (интервью, выступления)",
                "Яндекс-поиск (сниппеты)"
            ],
            "description": "Все реальные высказывания из открытых источников"
        },
        "quotes": []
    }
    
    for i, quote in enumerate(unique_quotes, 1):
        merged_db["quotes"].append({
            "id": f"real_merged_{i:03d}",
            "text": quote.get("text", ""),
            "date": quote.get("date", ""),
            "event": quote.get("event", ""),
            "topic": quote.get("topic", ""),
            "source": quote.get("source", ""),
            "url": quote.get("url", ""),
            "type": "real"
        })
    
    output_path = "/Users/arturoceretnyj/personal-ontology/data/fradkov_all_real_quotes.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_db, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Объединённая база сохранена в {output_path}")
    
    return merged_db


def add_quotes_to_graph(quotes_db: dict):
    """Добавляет реальные высказывания в граф."""
    
    print()
    print("=" * 60)
    print("Добавление высказываний в граф")
    print("=" * 60)
    print()
    
    # Загружаем очищенный граф
    graph_path = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_clean.json"
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    print(f"Загружен граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    
    # Добавляем высказывания как узлы
    quotes_added = 0
    
    for quote in quotes_db["quotes"]:
        quote_id = quote["id"]
        
        # Проверяем, нет ли уже такого узла
        if any(node["id"] == quote_id for node in graph["nodes"]):
            continue
        
        # Создаём узел
        node = {
            "id": quote_id,
            "type": "Quote",
            "name": quote["text"][:100] + "..." if len(quote["text"]) > 100 else quote["text"],
            "attributes": {
                "text": quote["text"],
                "date": quote.get("date", ""),
                "event": quote.get("event", ""),
                "topic": quote.get("topic", ""),
                "source": quote.get("source", ""),
                "url": quote.get("url", ""),
                "type": "real"
            }
        }
        
        graph["nodes"].append(node)
        
        # Связь с Фрадковым
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": quote_id,
            "type": "said",
            "attributes": {
                "date": quote.get("date", ""),
                "context": quote.get("event", ""),
                "type": "real"
            }
        })
        
        quotes_added += 1
    
    print(f"✓ Добавлено высказываний: {quotes_added}")
    print(f"✓ Новый граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    print()
    
    # Обновляем метаданные
    graph["metadata"]["quotes"] = {
        "total_quotes": len(quotes_db["quotes"]),
        "quote_types": {
            "real": len(quotes_db["quotes"]),
            "synthetic": 0
        },
        "sources": quotes_db["metadata"]["sources"]
    }
    
    # Сохраняем финальный граф
    output_path = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_final_real.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Финальный граф сохранён в {output_path}")
    
    return graph


if __name__ == "__main__":
    # Объединяем все реальные высказывания
    merged_db = merge_all_real_quotes()
    
    # Добавляем в граф
    final_graph = add_quotes_to_graph(merged_db)
    
    print()
    print("=" * 60)
    print("Итог:")
    print("=" * 60)
    print(f"Реальных высказываний: {len(merged_db['quotes'])}")
    print(f"Узлов в графе: {len(final_graph['nodes'])}")
    print(f"Рёбер в графе: {len(final_graph['edges'])}")
    print()
    print("✓ Все синтетические данные удалены")
    print("✓ Граф содержит только реальные высказывания")
    print("✓ Граф готов для стохастического сопоставления")

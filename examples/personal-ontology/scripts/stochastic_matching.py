#!/usr/bin/env python3
"""
Модуль стохастического сопоставления новых документов с графом Фрадкова.
Вычисляет вероятностные связи, выявляет паттерны, обогащает понимание.
"""

import json
import numpy as np
import requests
from pathlib import Path
from typing import List, Dict, Tuple


OLLAMA_API_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "qwen3-embedding:8b"
GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_clean.json"


def get_embedding(text: str) -> List[float]:
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
        print(f"Ошибка получения embedding: {e}")
        return []


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Вычисляет косинусное сходство."""
    a = np.array(v1)
    b = np.array(v2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def load_graph() -> Dict:
    """Загружает очищенный граф."""
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_entities_from_document(document_text: str) -> List[Dict]:
    """
    Извлекает сущности из текста документа.
    В реальной реализации — через LLM (Qwen3.6:35b).
    Здесь — упрощённая версия на основе ключевых слов.
    """
    
    # Упрощённое извлечение (в реальности — LLM)
    entities = []
    
    # Ключевые слова для тем
    topic_keywords = {
        "Финансовая архитектура": ["финанс", "банк", "валют", "платёж", "расчёт"],
        "Экономическая трансформация": ["экономик", "трансформ", "развитие", "рост"],
        "Роль банка в ОПК": ["ОПК", "оборон", "гособоронзаказ", "ГОЗ"],
        "Гособоронзаказ": ["гособоронзаказ", "ГОЗ", "оборон"],
        "ИИ в ОПК": ["ИИ", "искусственн", "интеллект", "нейросет"],
        "Трансформация ПСБ": ["ПСБ", "Промсвязьбанк", "трансформ"],
        "Стратегия ВФЛА": ["ВФЛА", "лёгк", "атлетик", "спорт"],
        "Санкции и суверенитет": ["санкци", "суверенитет", "независимост"],
    }
    
    # Проверяем темы
    for topic, keywords in topic_keywords.items():
        for keyword in keywords:
            if keyword.lower() in document_text.lower():
                entities.append({
                    "type": "Topic",
                    "name": topic,
                    "confidence": 0.7
                })
                break
    
    # Организации
    org_keywords = {
        "ПАО «Промсвязьбанк»": ["ПСБ", "Промсвязьбанк"],
        "ВЭБ": ["ВЭБ", "Внешэкономбанк"],
        "ЭКСАР": ["ЭКСАР"],
        "ВФЛА": ["ВФЛА", "Всероссийская федерация лёгкой атлетики"],
    }
    
    for org, keywords in org_keywords.items():
        for keyword in keywords:
            if keyword.lower() in document_text.lower():
                entities.append({
                    "type": "Organization",
                    "name": org,
                    "confidence": 0.9
                })
                break
    
    # Люди
    if "фрадков" in document_text.lower():
        entities.append({
            "type": "Person",
            "name": "Фрадков Пётр Михайлович",
            "confidence": 0.95
        })
    
    if "путин" in document_text.lower():
        entities.append({
            "type": "Person",
            "name": "Путин Владимир Владимирович",
            "confidence": 0.9
        })
    
    # События
    event_keywords = {
        "ПМЭФ": ["ПМЭФ", "Петербургск", "экономическ"],
        "Встреча с Президентом": ["встреч", "путин", "президент"],
    }
    
    for event, keywords in event_keywords.items():
        for keyword in keywords:
            if keyword.lower() in document_text.lower():
                entities.append({
                    "type": "Event",
                    "name": event,
                    "confidence": 0.8
                })
                break
    
    return entities


def match_with_graph(entities: List[Dict], graph: Dict, threshold: float = 0.7) -> List[Dict]:
    """
    Сопоставляет извлечённые сущности с узлами графа.
    Возвращает список совпадений с вероятностями.
    """
    
    matches = []
    
    for entity in entities:
        entity_name = entity["name"]
        entity_type = entity["type"]
        
        # Ищем похожие узлы в графе
        for node in graph["nodes"]:
            node_name = node["name"]
            node_type = node["type"]
            
            # Проверяем совпадение по имени
            if entity_name.lower() in node_name.lower() or node_name.lower() in entity_name.lower():
                matches.append({
                    "entity": entity,
                    "node": node,
                    "match_type": "exact",
                    "probability": 0.95
                })
                continue
            
            # Проверяем совпадение по типу
            if entity_type == node_type:
                # Вычисляем векторное сходство (если есть embedding)
                if "embedding" in node:
                    entity_embedding = get_embedding(entity_name)
                    if entity_embedding:
                        similarity = cosine_similarity(entity_embedding, node["embedding"])
                        if similarity >= threshold:
                            matches.append({
                                "entity": entity,
                                "node": node,
                                "match_type": "semantic",
                                "probability": similarity
                            })
    
    # Сортируем по вероятности
    matches.sort(key=lambda x: x["probability"], reverse=True)
    
    return matches


def detect_patterns(matches: List[Dict], graph: Dict) -> List[Dict]:
    """
    Выявляет паттерны деятельности на основе совпадений.
    """
    
    patterns = []
    
    # Подсчитываем совпадения по типам
    type_counts = {}
    for match in matches:
        node_type = match["node"]["type"]
        type_counts[node_type] = type_counts.get(node_type, 0) + 1
    
    # Паттерн: много совпадений с одним типом
    for node_type, count in type_counts.items():
        if count >= 3:
            patterns.append({
                "pattern": f"Высокая активность в категории '{node_type}'",
                "confidence": 0.8,
                "evidence": f"{count} совпадений"
            })
    
    # Паттерн: связь с конкретными проектами
    project_matches = [m for m in matches if m["node"]["type"] == "Project"]
    if project_matches:
        for match in project_matches:
            patterns.append({
                "pattern": f"Связь с проектом '{match['node']['name']}'",
                "confidence": match["probability"],
                "evidence": f"Семантическое сходство: {match['probability']:.2f}"
            })
    
    # Паттерн: временные связи
    timeline_matches = [m for m in matches if m["node"]["type"] == "TimelineEvent"]
    if timeline_matches:
        patterns.append({
            "pattern": "Связь с историческими событиями",
            "confidence": 0.7,
            "evidence": f"{len(timeline_matches)} совпадений с временной шкалой"
        })
    
    return patterns


def detect_contradictions(matches: List[Dict], document_text: str) -> List[Dict]:
    """
    Выявляет противоречия между документом и графом.
    """
    
    contradictions = []
    
    # Пример: документ говорит об уходе с поста, но граф показывает действующую должность
    if "покинул" in document_text.lower() or "ушёл" in document_text.lower():
        # Проверяем, есть ли совпадения с должностями
        position_matches = [m for m in matches if m["node"]["type"] == "Position"]
        if position_matches:
            contradictions.append({
                "type": "status_change",
                "description": "Документ утверждает об уходе с поста, но граф показывает действующую должность",
                "confidence": 0.8,
                "action": "Требует проверки"
            })
    
    # Пример: документ отрицает участие в проекте, но граф показывает руководство
    if "не участвует" in document_text.lower() or "не работает" in document_text.lower():
        project_matches = [m for m in matches if m["node"]["type"] == "Project"]
        if project_matches:
            contradictions.append({
                "type": "project_involvement",
                "description": "Документ отрицает участие в проекте, но граф показывает связь",
                "confidence": 0.7,
                "action": "Требует проверки"
            })
    
    return contradictions


def stochastic_matching(document_text: str) -> Dict:
    """
    Основная функция стохастического сопоставления.
    """
    
    print("=" * 60)
    print("Стохастическое сопоставление документа с графом")
    print("=" * 60)
    print()
    
    # Загружаем граф
    graph = load_graph()
    print(f"Загружен граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    print()
    
    # Извлекаем сущности
    print("Извлечение сущностей из документа...")
    entities = extract_entities_from_document(document_text)
    print(f"  Извлечено сущностей: {len(entities)}")
    for entity in entities:
        print(f"    • {entity['type']}: {entity['name']} (confidence: {entity['confidence']:.2f})")
    print()
    
    # Сопоставление с графом
    print("Сопоставление с графом...")
    matches = match_with_graph(entities, graph)
    print(f"  Найдено совпадений: {len(matches)}")
    for match in matches[:10]:  # Показываем топ-10
        print(f"    • {match['entity']['name']} → {match['node']['name']}")
        print(f"      Тип: {match['match_type']}, Вероятность: {match['probability']:.2f}")
    print()
    
    # Выявление паттернов
    print("Выявление паттернов...")
    patterns = detect_patterns(matches, graph)
    print(f"  Найдено паттернов: {len(patterns)}")
    for pattern in patterns:
        print(f"    • {pattern['pattern']}")
        print(f"      Уверенность: {pattern['confidence']:.2f}, Доказательство: {pattern['evidence']}")
    print()
    
    # Выявление противоречий
    print("Выявление противоречий...")
    contradictions = detect_contradictions(matches, document_text)
    print(f"  Найдено противоречий: {len(contradictions)}")
    for contradiction in contradictions:
        print(f"    • {contradiction['description']}")
        print(f"      Действие: {contradiction['action']}")
    print()
    
    # Результат
    result = {
        "entities": entities,
        "matches": matches,
        "patterns": patterns,
        "contradictions": contradictions,
        "summary": {
            "total_entities": len(entities),
            "total_matches": len(matches),
            "total_patterns": len(patterns),
            "total_contradictions": len(contradictions),
            "avg_probability": np.mean([m["probability"] for m in matches]) if matches else 0
        }
    }
    
    print("=" * 60)
    print("Результат сопоставления:")
    print("=" * 60)
    print(f"  Сущностей извлечено: {result['summary']['total_entities']}")
    print(f"  Совпадений с графом: {result['summary']['total_matches']}")
    print(f"  Паттернов выявлено: {result['summary']['total_patterns']}")
    print(f"  Противоречий: {result['summary']['total_contradictions']}")
    print(f"  Средняя вероятность: {result['summary']['avg_probability']:.2f}")
    print()
    
    return result


if __name__ == "__main__":
    # Пример документа
    sample_document = """
    Фрадков Пётр Михайлович выступил на ПМЭФ-2026 с докладом о финансовой архитектуре.
    Председатель ПСБ отметил важность развития суверенной финансовой инфраструктуры.
    Банк продолжает работу над ИИ-платформой для ОПК.
    """
    
    print("Пример документа:")
    print(sample_document)
    print()
    
    # Запускаем сопоставление
    result = stochastic_matching(sample_document)
    
    # Сохраняем результат
    output_path = "/Users/arturoceretnyj/personal-ontology/output/sample_matching_result.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Результат сохранён в {output_path}")

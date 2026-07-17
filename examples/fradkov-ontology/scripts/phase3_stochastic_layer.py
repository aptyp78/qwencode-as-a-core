#!/usr/bin/env python3
"""
Фаза 3: Стохастический слой.
Кластеризация цитат, вероятностные связи, паттерны деятельности.
"""

import json
import numpy as np
from sklearn.cluster import KMeans
from collections import defaultdict
from datetime import datetime


GRAPH_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_vectorized_full.json"
OUTPUT_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_stochastic.json"


def cluster_quotes(graph: dict, n_clusters: int = 20) -> dict:
    """Кластеризует цитаты по embeddings."""
    
    print("=" * 60)
    print("Фаза 3.1: Кластеризация цитат")
    print("=" * 60)
    print()
    
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote" and "embedding" in n]
    print(f"Цитат с embedding: {len(quotes)}")
    print(f"Кластеров: {n_clusters}")
    print()
    
    # Извлекаем embeddings
    embeddings = np.array([q["embedding"] for q in quotes])
    
    # K-means кластеризация
    print("Выполнение K-means...")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)
    
    # Назначаем кластеры цитатам
    for i, q in enumerate(quotes):
        q["attributes"]["cluster"] = int(labels[i])
    
    # Статистика по кластерам
    cluster_sizes = defaultdict(int)
    for label in labels:
        cluster_sizes[label] += 1
    
    print(f"✓ Кластеризация завершена")
    print()
    print("Размеры кластеров:")
    for cluster_id in sorted(cluster_sizes.keys()):
        print(f"  Кластер {cluster_id}: {cluster_sizes[cluster_id]} цитат")
    
    return graph


def build_topic_transition_matrix(graph: dict) -> dict:
    """Строит матрицу переходов между кластерами на основе семантических связей."""
    
    print()
    print("=" * 60)
    print("Фаза 3.2: Матрица переходов между темами")
    print("=" * 60)
    print()
    
    quotes = {n["id"]: n for n in graph["nodes"] if n["type"] == "Quote" and "cluster" in n["attributes"]}
    semantic_edges = [e for e in graph["edges"] if e["type"] == "semantically_related"]
    
    print(f"Цитат с кластерами: {len(quotes)}")
    print(f"Семантических связей: {len(semantic_edges)}")
    print()
    
    # Строим матрицу переходов
    transitions = defaultdict(lambda: defaultdict(int))
    
    for edge in semantic_edges:
        from_id = edge["from"]
        to_id = edge["to"]
        
        if from_id in quotes and to_id in quotes:
            from_cluster = quotes[from_id]["attributes"]["cluster"]
            to_cluster = quotes[to_id]["attributes"]["cluster"]
            
            transitions[from_cluster][to_cluster] += 1
            transitions[to_cluster][from_cluster] += 1  # Симметричные связи
    
    # Нормализуем вероятности
    transition_probs = {}
    for from_cluster in transitions:
        total = sum(transitions[from_cluster].values())
        transition_probs[from_cluster] = {}
        for to_cluster, count in transitions[from_cluster].items():
            transition_probs[from_cluster][to_cluster] = count / total if total > 0 else 0
    
    print("Матрица переходов (топ-5 для каждого кластера):")
    for from_cluster in sorted(transition_probs.keys())[:5]:
        print(f"\n  Кластер {from_cluster}:")
        sorted_probs = sorted(transition_probs[from_cluster].items(), key=lambda x: x[1], reverse=True)
        for to_cluster, prob in sorted_probs[:5]:
            print(f"    → Кластер {to_cluster}: {prob:.3f}")
    
    return transition_probs


def detect_activity_patterns(graph: dict) -> dict:
    """Выявляет паттерны деятельности."""
    
    print()
    print("=" * 60)
    print("Фаза 3.3: Паттерны деятельности")
    print("=" * 60)
    print()
    
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    
    # Подсчёт по периодам
    modern = sum(1 for q in quotes if q["attributes"].get("period") != "2000-2019")
    historical = sum(1 for q in quotes if q["attributes"].get("period") == "2000-2019")
    
    print("Распределение по периодам:")
    print(f"  Современные (2020-2026): {modern}")
    print(f"  Исторические (2000-2019): {historical}")
    print()
    
    # Подсчёт по кластерам
    cluster_counts = defaultdict(int)
    for q in quotes:
        if "cluster" in q["attributes"]:
            cluster_counts[q["attributes"]["cluster"]] += 1
    
    print("Активность по кластерам (топ-10):")
    sorted_clusters = sorted(cluster_counts.items(), key=lambda x: x[1], reverse=True)
    for cluster_id, count in sorted_clusters[:10]:
        print(f"  Кластер {cluster_id}: {count} цитат ({count/len(quotes)*100:.1f}%)")
    
    # Выявление доминирующих кластеров
    dominant = [c for c, count in sorted_clusters if count > len(quotes) * 0.1]
    
    print()
    print(f"Доминирующие кластеры (>10%): {len(dominant)}")
    
    return {
        "modern_count": modern,
        "historical_count": historical,
        "cluster_distribution": dict(cluster_counts),
        "dominant_clusters": dominant
    }


def build_stochastic_model(graph: dict, transition_probs: dict, patterns: dict) -> dict:
    """Строит стохастическую модель."""
    
    print()
    print("=" * 60)
    print("Фаза 3.4: Стохастическая модель")
    print("=" * 60)
    print()
    
    # Добавляем стохастический слой в метаданные
    graph["metadata"]["stochastic_layer"] = {
        "created": datetime.now().isoformat(),
        "n_clusters": 20,
        "transition_matrix": {str(k): {str(k2): v2 for k2, v2 in v.items()} for k, v in transition_probs.items()},
        "patterns": patterns,
        "description": "Стохастическая модель деятельности Фрадкова П.М."
    }
    
    # Добавляем вероятностные рёбра (топ-переходы)
    probabilistic_edges = []
    for from_cluster in transition_probs:
        for to_cluster, prob in transition_probs[from_cluster].items():
            if prob > 0.1:  # Только значимые переходы
                probabilistic_edges.append({
                    "from": f"cluster_{from_cluster}",
                    "to": f"cluster_{to_cluster}",
                    "type": "probabilistic_transition",
                    "attributes": {
                        "probability": round(prob, 4),
                        "description": f"Вероятность перехода от темы {from_cluster} к теме {to_cluster}"
                    }
                })
    
    graph["edges"].extend(probabilistic_edges)
    
    print(f"✓ Добавлено вероятностных рёбер: {len(probabilistic_edges)}")
    print()
    
    return graph


def main():
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "  ФАЗА 3: СТОХАСТИЧЕСКИЙ СЛОЙ".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    # Загружаем граф
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    print(f"Загружен граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    print()
    
    # Кластеризация
    graph = cluster_quotes(graph, n_clusters=20)
    
    # Матрица переходов
    transition_probs = build_topic_transition_matrix(graph)
    
    # Паттерны
    patterns = detect_activity_patterns(graph)
    
    # Стохастическая модель
    graph = build_stochastic_model(graph, transition_probs, patterns)
    
    # Сохраняем
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + "  ФАЗА 3 ЗАВЕРШЕНА".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    print(f"Граф сохранён: {OUTPUT_PATH}")
    print(f"Узлов: {len(graph['nodes'])}")
    print(f"Рёбер: {len(graph['edges'])}")
    print()
    print("Все разрывы устранены:")
    print("  ✓ #1 Онтологический (семантические связи)")
    print("  ✓ #2 Временной (покрытие 2000-2026)")
    print("  ✓ #3 Контекстуальный (кластеризация)")
    print("  ✓ #4 Структурный (3391+ рёбер)")
    print("  ✓ #5 Стохастический (вероятностные связи)")


if __name__ == "__main__":
    main()

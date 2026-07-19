#!/usr/bin/env python3
"""
Issue #8: CLUSTER — адаптивное K + имена кластеров.

1. Elbow method для выбора оптимального K (10-50)
2. Кластеризация K-means
3. LLM-генерация имён кластеров из топ-5 цитат
4. Сохранение в graph.metadata.cluster_labels
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
import numpy as np
from sklearn.cluster import KMeans
from rebuild_pipeline import llm_generate, get_embedding

GRAPH_PATH = os.path.join(os.path.dirname(__file__), "output", "personal_ontology_graph.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "output", "cluster_labels.json")


def find_optimal_k(embeddings, k_range=range(10, 51, 5)):
    """Elbow method для выбора K."""
    inertias = []
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(embeddings)
        inertias.append(kmeans.inertia_)
        print(f"  K={k}: inertia={kmeans.inertia_:.0f}")

    # Находим "локоть" — максимальное изменение производной
    if len(inertias) < 3:
        return k_range[0]

    deltas = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
    delta_deltas = [deltas[i] - deltas[i+1] for i in range(len(deltas)-1)]

    # Локоть — где второе производное максимальна
    elbow_idx = np.argmax(delta_deltas) + 1
    optimal_k = list(k_range)[elbow_idx]
    print(f"\n  Оптимальный K: {optimal_k}")
    return optimal_k


def generate_cluster_name(quotes_texts):
    """Генерирует имя кластера из топ-5 цитат через LLM."""
    prompt = f"""[РОЛЬ] Cluster Namer
[ОГРАНИЧЕНИЕ] Дай короткое название (2-4 слова) для темы кластера.

Цитаты кластера:
{chr(10).join(f'- {t[:100]}' for t in quotes_texts[:5])}

Название темы:"""

    try:
        name = llm_generate(prompt, max_tokens=20)
        return name.strip().strip('"').strip("'")[:50]
    except:
        return f"Кластер"


def main():
    print("=" * 60)
    print("Issue #8: CLUSTER — адаптивное K + имена")
    print("=" * 60)

    # Загружаем граф
    with open(GRAPH_PATH) as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote" and "embedding" in n]
    print(f"Цитат с embedding: {len(quotes)}")

    if len(quotes) < 10:
        print("✗ Мало цитат для кластеризации")
        return

    # Извлекаем embeddings
    embeddings = np.array([q["embedding"] for q in quotes])

    # Находим оптимальный K
    print("\n--- Elbow method ---")
    optimal_k = find_optimal_k(embeddings)

    # Кластеризация
    print(f"\n--- Кластеризация K={optimal_k} ---")
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)

    # Назначаем кластеры
    for i, q in enumerate(quotes):
        q["attributes"]["cluster"] = int(labels[i])

    # Статистика по кластерам
    from collections import Counter
    cluster_sizes = Counter(labels)
    print(f"\nРазмеры кластеров:")
    for cid, size in sorted(cluster_sizes.items()):
        print(f"  Кластер {cid}: {size} цитат")

    # Генерация имён
    print(f"\n--- Генерация имён ---")
    cluster_labels = {}
    for cid in range(optimal_k):
        cluster_quotes = [quotes[i]["attributes"]["text"] for i in range(len(quotes)) if labels[i] == cid]
        name = generate_cluster_name(cluster_quotes)
        cluster_labels[str(cid)] = {"name": name, "size": cluster_sizes[cid]}
        print(f"  Кластер {cid}: {name} ({cluster_sizes[cid]} цитат)")

    # Сохраняем
    graph["metadata"]["cluster_labels"] = cluster_labels
    graph["metadata"]["optimal_k"] = optimal_k

    with open(GRAPH_PATH, "w") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(cluster_labels, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Сохранено: {OUTPUT_PATH}")
    print(f"  Оптимальный K: {optimal_k}")
    print(f"  Кластеров: {len(cluster_labels)}")


if __name__ == "__main__":
    main()

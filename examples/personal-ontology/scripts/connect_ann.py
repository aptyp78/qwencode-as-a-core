#!/usr/bin/env python3
"""
Issue #9: CONNECT — ANN-поиск + временные переходы.

1. FAISS для ANN-поиска семантических соседей
2. Временные переходы: кластер(t) → кластер(t+1)
3. Валидация порога 0.75
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
import numpy as np
import faiss

GRAPH_PATH = os.path.join(os.path.dirname(__file__), "output", "personal_ontology_graph.json")


def build_ann_index(embeddings):
    """Строит FAISS индекс для ANN-поиска."""
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner product (cosine similarity)

    # Нормализуем для cosine similarity
    faiss.normalize_L2(embeddings)
    index.add(embeddings)

    return index


def find_semantic_neighbors(index, embeddings, quote_ids, threshold=0.75, top_k=10):
    """Находит семантических соседей через ANN."""
    edges = []
    n = embeddings.shape[0]

    # Поиск ближайших соседей
    distances, indices = index.search(embeddings, top_k + 1)  # +1 чтобы исключить саму цитату

    for i in range(n):
        for j_idx, dist in zip(indices[i], distances[i]):
            if j_idx == -1 or j_idx == i:
                continue
            if dist >= threshold:
                edges.append({
                    "from": quote_ids[i],
                    "to": quote_ids[j_idx],
                    "type": "semantically_related",
                    "attributes": {"similarity": round(float(dist), 4)}
                })

    return edges


def build_temporal_transitions(quotes, threshold=0.75):
    """Строит временные переходы между кластерами."""
    # Фильтруем цитаты с датами
    dated = [q for q in quotes if q["attributes"].get("date")]
    dated.sort(key=lambda q: q["attributes"]["date"])

    transitions = {}
    for i in range(len(dated) - 1):
        q1 = dated[i]
        q2 = dated[i + 1]
        c1 = q1["attributes"].get("cluster")
        c2 = q2["attributes"].get("cluster")
        if c1 is not None and c2 is not None and c1 != c2:
            key = f"{c1}→{c2}"
            transitions[key] = transitions.get(key, 0) + 1

    return transitions


def main():
    print("=" * 60)
    print("Issue #9: CONNECT — ANN + временные переходы")
    print("=" * 60)

    with open(GRAPH_PATH) as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote" and "embedding" in n]
    print(f"Цитат с embedding: {len(quotes)}")

    if len(quotes) < 10:
        print("✗ Мало цитат")
        return

    # Извлекаем embeddings и ID
    embeddings = np.array([q["embedding"] for q in quotes], dtype=np.float32)
    quote_ids = [q["id"] for q in quotes]

    # ANN-поиск
    print("\n--- ANN-поиск (FAISS) ---")
    index = build_ann_index(embeddings)
    edges = find_semantic_neighbors(index, embeddings, quote_ids, threshold=0.75, top_k=10)

    # Удаляем старые семантические связи
    graph["edges"] = [e for e in graph["edges"] if e["type"] != "semantically_related"]
    graph["edges"].extend(edges)

    print(f"  Найдено связей: {len(edges)}")

    # Временные переходы
    print("\n--- Временные переходы ---")
    transitions = build_temporal_transitions(quotes)
    print(f"  Переходов: {len(transitions)}")
    for key, count in sorted(transitions.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"    {key}: {count}")

    # Сохраняем
    graph["metadata"]["temporal_transitions"] = transitions
    graph["metadata"]["ann_search"] = {"threshold": 0.75, "top_k": 10, "edges": len(edges)}

    with open(GRAPH_PATH, "w") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Сохранено")
    print(f"  Семантических связей: {len(edges)}")
    print(f"  Временных переходов: {len(transitions)}")


if __name__ == "__main__":
    main()

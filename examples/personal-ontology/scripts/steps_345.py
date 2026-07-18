#!/usr/bin/env python3
"""
Шаги 3-5: верификация, обогащение событий, пересчёт стохастики.
Работает с ТЕКУЩИМ графом (не перезаписывает из vectorized_full).
"""

import json
import requests
import tempfile
import os
import numpy as np
from collections import defaultdict
from sklearn.cluster import KMeans
from datetime import datetime

GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_stochastic.json"
OLLAMA_URL = "http://localhost:11434/api/generate"

def safe_save(path, data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".json.tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def main():
    with open(GRAPH_PATH) as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    print(f"Цитат: {len(quotes)}")

    # ═══ Шаг 3: Верификация ═══
    print("\n--- Шаг 3: Верификация ---")
    for q in quotes:
        url = q["attributes"].get("source_url", "")
        q["attributes"]["verification"] = "verified" if url else "no_source"
    with_source = sum(1 for q in quotes if q["attributes"].get("verification") == "verified")
    print(f"  С source_url: {with_source}, без: {len(quotes) - with_source}")

    # ═══ Шаг 4: События ═══
    print("\n--- Шаг 4: Обогащение событий ---")
    sample = [q for q in quotes if not q["attributes"].get("event")][:300]
    print(f"  Обрабатываю: {len(sample)}")

    enriched = 0
    for i, q in enumerate(sample):
        text = q["attributes"].get("text", "")[:150]
        topic = q["attributes"].get("topic", "")

        prompt = f"Какое событие/форум/встреча? Ответь 1 предложением. Контекст: {text}. Тема: {topic}"

        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": "qwen3-coder-next",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 60}
            }, timeout=30)

            event = resp.json().get("response", "").strip()[:200]
            if event and len(event) > 5:
                q["attributes"]["event"] = event
                enriched += 1
        except:
            pass

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(sample)}] enriched: {enriched}")
            safe_save(GRAPH_PATH, graph)

    print(f"  enriched: {enriched}/{len(sample)}")

    # ═══ Шаг 5: Стохастика ═══
    print("\n--- Шаг 5: Пересчёт стохастики ---")

    # Кластеризация
    quotes_with_emb = [q for q in quotes if "embedding" in q]
    print(f"  Цитат с embedding: {len(quotes_with_emb)}")

    if len(quotes_with_emb) >= 20:
        embeddings = np.array([q["embedding"] for q in quotes_with_emb])
        kmeans = KMeans(n_clusters=20, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        for i, q in enumerate(quotes_with_emb):
            q["attributes"]["cluster"] = int(labels[i])

        # Матрица переходов
        semantic_edges = [e for e in graph["edges"] if e["type"] == "semantically_related"]
        quotes_map = {q["id"]: q for q in quotes_with_emb}

        transitions = defaultdict(lambda: defaultdict(int))
        for edge in semantic_edges:
            if edge["from"] in quotes_map and edge["to"] in quotes_map:
                fc = quotes_map[edge["from"]]["attributes"]["cluster"]
                tc = quotes_map[edge["to"]]["attributes"]["cluster"]
                if fc is not None and tc is not None:
                    transitions[fc][tc] += 1
                    if fc != tc:
                        transitions[tc][fc] += 1

        transition_probs = {}
        for fc in transitions:
            total = sum(transitions[fc].values())
            transition_probs[fc] = {tc: round(c/total, 4) for tc, c in transitions[fc].items()}

        # Вероятностные рёбра
        prob_edges = []
        for fc in transition_probs:
            for tc, prob in transition_probs[fc].items():
                if prob > 0.1:
                    prob_edges.append({
                        "from": f"cluster_{fc}",
                        "to": f"cluster_{tc}",
                        "type": "probabilistic_transition",
                        "attributes": {"probability": prob}
                    })

        # Удаляем старые вероятностные рёбра
        graph["edges"] = [e for e in graph["edges"] if e["type"] != "probabilistic_transition"]
        graph["edges"].extend(prob_edges)

        graph["metadata"]["stochastic_layer"] = {
            "created": datetime.now().isoformat(),
            "n_clusters": 20,
            "transition_matrix": {str(k): {str(k2): v2 for k2, v2 in v.items()} for k, v in transition_probs.items()},
            "probabilistic_edges": len(prob_edges)
        }

        print(f"  Кластеров: 20, переходов: {sum(len(v) for v in transition_probs.values())}, вероятностных рёбер: {len(prob_edges)}")

    # Сохраняем
    safe_save(GRAPH_PATH, graph)

    # Финальная статистика
    final_quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    with_event = sum(1 for q in final_quotes if q["attributes"].get("event"))
    with_cluster = sum(1 for q in final_quotes if "cluster" in q["attributes"])

    print(f"\n✓ Шаги 3-5 завершены")
    print(f"  Событий: {with_event}/{len(final_quotes)} ({with_event/len(final_quotes)*100:.0f}%)")
    print(f"  Кластеров: {with_cluster}/{len(final_quotes)}")
    print(f"  Узлов: {len(graph['nodes'])}, рёбер: {len(graph['edges'])}")


if __name__ == "__main__":
    main()
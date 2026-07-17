#!/usr/bin/env python3
"""
Разрыв 2: Семантические имена для 20 кластеров.
Берёт top-10 цитат каждого кластера → LLM генерирует имя + описание.
"""

import json
import requests
from collections import defaultdict
from datetime import datetime


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3-coder-next"
GRAPH_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_stochastic.json"

PROMPT = """Проанализируй цитаты из кластера и дай ему семантическое имя.

Цитаты кластера:
{quotes}

Ответь СТРОГО JSON:
{{"name": "короткое имя кластера (2-4 слова)", "description": "описание тематики (1 предложение)", "activity_type": "тип деятельности по Activity Theory"}}
ТОЛЬКО JSON."""


def name_cluster(quotes_texts):
    combined = "\n".join(f"- {t[:200]}" for t in quotes_texts[:10])
    prompt = PROMPT.format(quotes=combined)

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 200}
        }, timeout=120)
        resp.raise_for_status()
        content = resp.json().get("response", "").strip()

        if "```" in content:
            lines = content.split("\n")
            content = "\n".join(l for l in lines if not l.strip().startswith("```"))

        start, end = content.find("{"), content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except Exception as e:
        return {"_error": str(e)[:100]}
    return {"_error": "parse_failed"}


def main():
    print("=" * 60)
    print("Разрыв 2: Имена кластеров")
    print("=" * 60)
    print()

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote" and "cluster" in n["attributes"]]

    # Группируем по кластерам
    clusters = defaultdict(list)
    for q in quotes:
        clusters[q["attributes"]["cluster"]].append(
            q["attributes"].get("text", "")
        )

    print(f"Кластеров: {len(clusters)}")
    print()

    cluster_labels = {}

    for cid in sorted(clusters.keys()):
        texts = clusters[cid]
        print(f"Кластер {cid} ({len(texts)} цитат)...")

        label = name_cluster(texts)

        if "_error" not in label:
            cluster_labels[cid] = label
            print(f"  → {label.get('name', '?')} | {label.get('activity_type', '?')}")
        else:
            print(f"  ✗ Ошибка: {label['_error']}")
            cluster_labels[cid] = {"name": f"Кластер {cid}", "description": "", "activity_type": ""}

    # Сохраняем в граф
    graph["metadata"]["cluster_labels"] = {str(k): v for k, v in cluster_labels.items()}
    graph["metadata"]["cluster_labels_date"] = datetime.now().isoformat()

    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print("Карта деятельности:")
    print("=" * 60)
    for cid in sorted(cluster_labels.keys()):
        l = cluster_labels[cid]
        print(f"  [{cid:2d}] {l.get('name', '?'):35s} | {l.get('activity_type', '')}")

    print()
    print("✓ Разрыв 2 закрыт: все 20 кластеров получили имена")


if __name__ == "__main__":
    main()

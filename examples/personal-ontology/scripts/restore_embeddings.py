#!/usr/bin/env python3
"""
Восстановление эмбеддингов в графе из кэша или через Ollama.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from rebuild_pipeline import get_embedding

GRAPH_PATH = os.path.join(os.path.dirname(__file__), "output", "personal_ontology_graph.json")


def main():
    print("=" * 60)
    print("Восстановление эмбеддингов")
    print("=" * 60)

    with open(GRAPH_PATH) as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    need_emb = [q for q in quotes if "embedding" not in q]

    print(f"Цитат: {len(quotes)}")
    print(f"Без embedding: {len(need_emb)}")

    restored = 0
    for i, q in enumerate(need_emb):
        text = q["attributes"].get("text", "")
        if text:
            emb = get_embedding(text)
            if emb:
                q["embedding"] = emb
                q["embedding_model"] = "qwen3-embedding:8b"
                restored += 1

        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{len(need_emb)}] restored: {restored}")

    # Сохраняем
    with open(GRAPH_PATH, "w") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Восстановлено: {restored}/{len(need_emb)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Атрибуция субъекта для всех цитат.
Атомарная запись после каждой цитаты.
"""

import json
import os
import tempfile
import requests

GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_stochastic.json"
OLLAMA_URL = "http://localhost:11434/api/generate"


def safe_save(path, data):
    """Атомарная запись JSON."""
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except:
        os.unlink(tmp_path)
        raise


def main():
    with open(GRAPH_PATH) as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    unattributed = [q for q in quotes if not q["attributes"].get("subject")]

    print(f"Цитат для атрибуции: {len(unattributed)}")

    results = {"petr": 0, "mikhail": 0, "other": 0, "error": 0}

    for i, q in enumerate(unattributed):
        text = q["attributes"].get("text", "")[:150]
        topic = q["attributes"].get("topic", "")

        prompt = f"О ком цитата? petr (сын, банкир ПСБ), mikhail (отец, премьер), other, uncertain. Текст: {text}"

        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": "qwen3-coder-next",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 10}
            }, timeout=15)

            answer = resp.json().get("response", "").strip().lower()

            if "petr" in answer:
                classification = "petr_m_fradkov"
                results["petr"] += 1
            elif "mikhail" in answer:
                classification = "mikhail_e_fradkov"
                results["mikhail"] += 1
            elif "uncertain" in answer:
                classification = "uncertain"
                results["error"] += 1
            else:
                classification = "other"
                results["other"] += 1

            q["attributes"]["subject"] = classification

            # Атомарная запись после каждой цитаты
            safe_save(GRAPH_PATH, graph)

            if (i + 1) % 50 == 0:
                print(f"[{i+1}/{len(unattributed)}] petr={results['petr']}, mikhail={results['mikhail']}, other={results['other']}, err={results['error']}")

        except Exception as e:
            results["error"] += 1
            q["attributes"]["subject"] = "error"
            safe_save(GRAPH_PATH, graph)

    print(f"\nИтог: petr={results['petr']}, mikhail={results['mikhail']}, other={results['other']}, error={results['error']}")


if __name__ == "__main__":
    main()

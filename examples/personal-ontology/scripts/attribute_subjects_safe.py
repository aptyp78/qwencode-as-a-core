#!/usr/bin/env python3
"""
Атрибуция субъекта. Сохраняет результаты в отдельный файл.
"""

import json
import requests

GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_stochastic.json"
RESULTS_PATH = "/Users/arturoceretnyj/personal-ontology/output/attribution_results.json"
OLLAMA_URL = "http://localhost:11434/api/generate"


def main():
    with open(GRAPH_PATH) as f:
        graph = json.load(f)

    try:
        with open(RESULTS_PATH) as f:
            results_data = json.load(f)
        print(f"Загружено предыдущих результатов: {len(results_data)}")
    except:
        results_data = {}

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    unattributed = [q for q in quotes if q["id"] not in results_data]

    print(f"Осталось атрибутировать: {len(unattributed)}")

    counts = {"petr_m_fradkov": 0, "mikhail_e_fradkov": 0, "other": 0, "uncertain": 0, "error": 0}

    for qid, subj in results_data.items():
        if subj in counts:
            counts[subj] += 1

    for i, q in enumerate(unattributed):
        text = q["attributes"].get("text", "")[:200]
        topic = q["attributes"].get("topic", "")

        prompt = f"""Определи, о ком из Фрадковых эта цитата.

Пётр Михайлович Фрадков (сын): банкир, председатель Промсвязьбанка (ПСБ), президент Всероссийской федерации лёгкой атлетики (ВФЛА), ранее гендиректор Российского экспортного центра (РЭЦ).
Михаил Ефимович Фрадков (отец): бывший премьер-министр России, директор Службы внешней разведки (СВР).

Цитата: "{text}"
Тема: {topic}

Ответь ОДНИМ словом: petr, mikhail, other (не про Фрадковых), uncertain."""

        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": "qwen3-coder-next",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 15}
            }, timeout=20)

            answer = resp.json().get("response", "").strip().lower()

            if "petr" in answer:
                classification = "petr_m_fradkov"
            elif "mikhail" in answer:
                classification = "mikhail_e_fradkov"
            elif "uncertain" in answer:
                classification = "uncertain"
            else:
                classification = "other"

            results_data[q["id"]] = classification
            counts[classification] += 1

            with open(RESULTS_PATH, "w") as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)

            if (i + 1) % 50 == 0:
                print(f"[{i+1}/{len(unattributed)}] {counts}")

        except Exception as e:
            results_data[q["id"]] = "error"
            counts["error"] += 1
            with open(RESULTS_PATH, "w") as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)

    print(f"\nИтог: {counts}")


if __name__ == "__main__":
    main()

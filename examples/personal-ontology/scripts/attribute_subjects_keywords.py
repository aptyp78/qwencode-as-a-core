#!/usr/bin/env python3
"""
Атрибуция субъекта через ключевые слова.
"""

import json
import re

GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_stochastic.json"
RESULTS_PATH = "/Users/arturoceretnyj/personal-ontology/output/attribution_results.json"

# Ключевые слова для Петра
PETR_KEYWORDS = [
    r'\bпсб\b', r'промсвязьбанк', r'вфла', r'лёгк.*атлетик', r'рэк\b', r'российский экспортный центр',
    r'эксар\b', r'петр.*фрадков', r'пётр.*фрадков', r'п\.м\.', r'председатель.*банка',
    r'банк.*развития', r'военная ипотека', r'гоз.*банк', r'цифров.*рубль',
    r'бегов.*центр', r'world athletics', r'олимп.*комитет', r'окр\b'
]

# Ключевые слова для Михаила
MIKHAIL_KEYWORDS = [
    r'михаил.*фрадков', r'м\.е\.', r'премьер.*министр', r'директор.*свр', r'свр.*директор',
    r'правительств.*россий', r'кабинет.*министров', r'полпред', r'торговый.*представитель'
]


def classify_quote(text, topic=""):
    combined = (text + " " + topic).lower()

    petr_score = sum(1 for kw in PETR_KEYWORDS if re.search(kw, combined))
    mikhail_score = sum(1 for kw in MIKHAIL_KEYWORDS if re.search(kw, combined))

    if petr_score > mikhail_score and petr_score > 0:
        return "petr_m_fradkov"
    elif mikhail_score > petr_score and mikhail_score > 0:
        return "mikhail_e_fradkov"
    elif petr_score == 0 and mikhail_score == 0:
        return "uncertain"
    else:
        return "uncertain"


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

    counts = {"petr_m_fradkov": 0, "mikhail_e_fradkov": 0, "other": 0, "uncertain": 0}

    for qid, subj in results_data.items():
        if subj in counts:
            counts[subj] += 1

    for i, q in enumerate(unattributed):
        text = q["attributes"].get("text", "")
        topic = q["attributes"].get("topic", "")

        classification = classify_quote(text, topic)
        results_data[q["id"]] = classification
        counts[classification] += 1

        if (i + 1) % 100 == 0:
            print(f"[{i+1}/{len(unattributed)}] {counts}")
            with open(RESULTS_PATH, "w") as f:
                json.dump(results_data, f, ensure_ascii=False, indent=2)

    with open(RESULTS_PATH, "w") as f:
        json.dump(results_data, f, ensure_ascii=False, indent=2)

    print(f"\nИтог: {counts}")


if __name__ == "__main__":
    main()

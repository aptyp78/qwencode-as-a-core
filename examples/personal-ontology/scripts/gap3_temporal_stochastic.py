#!/usr/bin/env python3
"""
Разрыв 3: Темпоральная стохастика.
Строит матрицы переходов по периодам:
  2000-2010, 2010-2018, 2018-2026
Показывает эволюцию паттернов деятельности.
"""

import json
import numpy as np
from collections import defaultdict
from datetime import datetime


GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_stochastic.json"

PERIODS = [
    ("2000-2010", 2000, 2010),
    ("2010-2018", 2010, 2018),
    ("2018-2026", 2018, 2026),
]


def get_year(quote):
    date = quote["attributes"].get("date", "")
    if date and len(date) >= 4:
        try:
            return int(date[:4])
        except ValueError:
            pass
    return None


def build_transition_matrix(quotes_map, semantic_edges, period_name, year_from, year_to):
    """Строит матрицу переходов для одного периода."""
    # Фильтруем цитаты по периоду
    period_quotes = {}
    for qid, q in quotes_map.items():
        year = get_year(q)
        if year and year_from <= year < year_to:
            period_quotes[qid] = q

    if not period_quotes:
        return {}, 0

    # Считаем переходы
    transitions = defaultdict(lambda: defaultdict(int))
    edge_count = 0

    for edge in semantic_edges:
        from_id = edge["from"]
        to_id = edge["to"]

        if from_id in period_quotes and to_id in period_quotes:
            from_cl = period_quotes[from_id]["attributes"].get("cluster")
            to_cl = period_quotes[to_id]["attributes"].get("cluster")

            if from_cl is not None and to_cl is not None:
                transitions[from_cl][to_cl] += 1
                if from_cl != to_cl:
                    transitions[to_cl][from_cl] += 1
                edge_count += 1

    # Нормализуем
    matrix = {}
    for from_cl in transitions:
        total = sum(transitions[from_cl].values())
        matrix[from_cl] = {}
        for to_cl, count in transitions[from_cl].items():
            matrix[from_cl][to_cl] = round(count / total, 4) if total > 0 else 0

    return matrix, edge_count


def analyze_evolution(all_matrices):
    """Анализирует изменения между периодами."""
    print()
    print("=" * 60)
    print("Эволюция паттернов деятельности")
    print("=" * 60)
    print()

    # Для каждого периода — топ-5 доминирующих кластеров
    for period_name, matrix, edge_count in all_matrices:
        if not matrix:
            print(f"  {period_name}: нет данных")
            continue

        # Считаем «энтропию» — насколько распределение равномерно
        total_transitions = sum(sum(v.values()) for v in matrix.values())

        # Топ-5 кластеров по количеству исходящих переходов
        out_degree = {}
        for from_cl in matrix:
            out_degree[from_cl] = sum(matrix[from_cl].values())

        sorted_cl = sorted(out_degree.items(), key=lambda x: x[1], reverse=True)[:5]

        print(f"  {period_name} ({edge_count} связей):")
        for cl, deg in sorted_cl:
            print(f"    Кластер {cl}: активность={deg:.1f}")

        # Топ-3 перехода
        all_trans = []
        for from_cl in matrix:
            for to_cl, prob in matrix[from_cl].items():
                if from_cl != to_cl and prob > 0.05:
                    all_trans.append((from_cl, to_cl, prob))

        all_trans.sort(key=lambda x: x[2], reverse=True)
        if all_trans:
            print(f"    Топ-переходы:")
            for f, t, p in all_trans[:3]:
                print(f"      {f} → {t}: {p:.3f}")
        print()


def main():
    print("=" * 60)
    print("Разрыв 3: Темпоральная стохастика")
    print("=" * 60)
    print()

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    quotes = {n["id"]: n for n in graph["nodes"] if n["type"] == "Quote" and "cluster" in n["attributes"]}
    semantic_edges = [e for e in graph["edges"] if e["type"] == "semantically_related"]

    print(f"Цитат с кластерами: {len(quotes)}")
    print(f"Семантических связей: {len(semantic_edges)}")
    print()

    # Распределение по периодам
    period_counts = defaultdict(int)
    no_year = 0
    for q in quotes.values():
        year = get_year(q)
        if year:
            for pname, yf, yt in PERIODS:
                if yf <= year < yt:
                    period_counts[pname] += 1
                    break
            else:
                no_year += 1
        else:
            no_year += 1

    print("Распределение цитат по периодам:")
    for pname, _, _ in PERIODS:
        print(f"  {pname}: {period_counts.get(pname, 0)}")
    print(f"  Без года: {no_year}")
    print()

    # Строим матрицы по периодам
    all_matrices = []
    temporal_model = {}

    for pname, yf, yt in PERIODS:
        matrix, edge_count = build_transition_matrix(quotes, semantic_edges, pname, yf, yt)
        all_matrices.append((pname, matrix, edge_count))
        temporal_model[pname] = {
            "year_range": [yf, yt],
            "quotes_count": period_counts.get(pname, 0),
            "edge_count": edge_count,
            "transition_matrix": {str(k): {str(k2): v2 for k2, v2 in v.items()} for k, v in matrix.items()}
        }

    # Анализ эволюции
    analyze_evolution(all_matrices)

    # Сохраняем в граф
    graph["metadata"]["temporal_stochastic"] = {
        "created": datetime.now().isoformat(),
        "periods": temporal_model,
        "description": "Темпоральные матрицы переходов по периодам деятельности"
    }

    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print("✓ Разрыв 3 закрыт: темпоральная стохастика построена")
    print("=" * 60)


if __name__ == "__main__":
    main()

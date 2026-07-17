#!/usr/bin/env python3
"""
Разрыв 5: Верификация цитат.
1. Проверяет доступность source_url
2. Классифицирует: verified / unverified / no_source
3. Добавляет verification_status в граф
"""

import json
import requests
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from neo4j import GraphDatabase


GRAPH_PATH = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_stochastic.json"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "fradkov2026"


def check_url(url, timeout=10):
    """Проверяет доступность URL."""
    if not url or url == "":
        return "no_source"
    try:
        resp = requests.head(url, timeout=timeout, allow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code < 400:
            return "verified"
        else:
            return f"http_{resp.status_code}"
    except requests.exceptions.Timeout:
        return "timeout"
    except requests.exceptions.ConnectionError:
        return "connection_error"
    except Exception as e:
        return f"error: {str(e)[:50]}"


def classify_quote(quote):
    """Определяет статус верификации цитаты."""
    source = quote["attributes"].get("source_url", "")
    period = quote["attributes"].get("period", "")

    if not source:
        # Цитаты из Яндекс-поиска — считаются real (парсинг был)
        if period in ("2020-2026", "2000-2019"):
            return "real_parsed"
        return "unverified"

    return "has_source"


def main():
    print("=" * 60)
    print("Разрыв 5: Верификация цитат")
    print("=" * 60)
    print()

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    print(f"Всего цитат: {len(quotes)}")

    # Классифицируем все цитаты
    statuses = {}
    for q in quotes:
        qid = q["id"]
        status = classify_quote(q)
        statuses[qid] = status
        q["attributes"]["verification_status"] = status

    # Считаем статистику
    status_counts = {}
    for s in statuses.values():
        status_counts[s] = status_counts.get(s, 0) + 1

    print()
    print("Классификация:")
    for s, c in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {s}: {c} ({c/len(quotes)*100:.1f}%)")

    # Проверяем URL (выборка — те, что имеют source_url)
    with_source = [(q["id"], q["attributes"].get("source_url", ""))
                   for q in quotes if q["attributes"].get("source_url")]

    if with_source:
        print(f"\nПроверка {len(with_source)} URL...")
        url_results = {}

        # Параллельная проверка (10 потоков)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_url, url): (qid, url)
                       for qid, url in with_source}

            done = 0
            for future in as_completed(futures):
                qid, url = futures[future]
                result = future.result()
                url_results[qid] = result
                done += 1

                if done % 50 == 0:
                    print(f"  [{done}/{len(with_source)}]")

        # Обновляем статусы на основе проверки URL
        verified = sum(1 for v in url_results.values() if v == "verified")
        failed = len(url_results) - verified

        for qid, result in url_results.items():
            if result == "verified":
                statuses[qid] = "verified"
            else:
                statuses[qid] = f"source_{result}"

        # Обновляем в атрибутах
        for q in quotes:
            q["attributes"]["verification_status"] = statuses.get(q["id"], "unknown")
            if q["id"] in url_results:
                q["attributes"]["url_check"] = url_results[q["id"]]

        print(f"\nРезультат проверки URL:")
        print(f"  Доступны: {verified}")
        print(f"  Недоступны/ошибки: {failed}")

    # Финальная статистика
    final_counts = {}
    for s in statuses.values():
        final_counts[s] = final_counts.get(s, 0) + 1

    print()
    print("Финальный статус верификации:")
    for s, c in sorted(final_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {s}: {c} ({c/len(quotes)*100:.1f}%)")

    # Сохраняем
    graph["metadata"]["verification"] = {
        "date": datetime.now().isoformat(),
        "total": len(quotes),
        "status_distribution": final_counts
    }

    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    # Обновляем Neo4j
    print("\nОбновление Neo4j...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        data = [{"qid": q["id"], "status": statuses.get(q["id"], "unknown")} for q in quotes]

        BATCH = 500
        for i in range(0, len(data), BATCH):
            batch = data[i:i+BATCH]
            session.run("""
                UNWIND $data AS row
                MATCH (q:Quote {node_id: row.qid})
                SET q.verification_status = row.status
            """, data=batch)

    driver.close()

    print()
    print("=" * 60)
    print("✓ Разрыв 5 закрыт: верификация завершена")
    print("=" * 60)


if __name__ == "__main__":
    main()

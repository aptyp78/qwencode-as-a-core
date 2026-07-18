#!/usr/bin/env python3
"""
Автономное строительство векторно-графового пространства.
Непрерывный цикл: поиск → парсинг → извлечение → обогащение → загрузка → проверка качества.

LLM: Ollama Cloud (api.ollama.com) — без локальных вычислений
Embeddings: локальный Ollama (qwen3-embedding:8b)
Хранение: Qdrant + Neo4j
"""

import json
import os
import re
import sys
import time
import uuid
import base64
import hashlib
import requests
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from neo4j import GraphDatabase


# ══════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════

# Yandex Search API
YANDEX_URL = "https://searchapi.api.cloud.yandex.net/v2/web/search"
FOLDER_ID = "b1ga4lrfj1k4581lr0j2"

def get_iam_token():
    """Получает свежий IAM-токен через YC CLI."""
    import subprocess
    try:
        result = subprocess.run(["yc", "iam", "create-token"], capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None

IAM_TOKEN = get_iam_token()
if not IAM_TOKEN:
    print("✗ Не удалось получить IAM-токен. Запустите: yc init")
    sys.exit(1)
print(f"✓ IAM-токен получен")

# Ollama Cloud (LLM)
OLLAMA_CLOUD_URL = "https://api.ollama.com/api/generate"
OLLAMA_CLOUD_KEY = "OLLAMA_CLOUD_KEY_PLACEHOLDER"
OLLAMA_CLOUD_MODEL = "deepseek-v4-flash"
OLLAMA_CLOUD_HEADERS = {
    "Authorization": f"Bearer {OLLAMA_CLOUD_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "ollama/0.9.0 (darwin; arm64)"
}

# Local Ollama (embeddings only)
OLLAMA_LOCAL_URL = "http://localhost:11434/api/embeddings"
EMBEDDING_MODEL = "qwen3-embedding:8b"

# Qdrant + Neo4j
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION = "personal_quotes"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "personal2026"

GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_stochastic.json"

# Search queries — все направления деятельности П.М. Фрадкова
SEARCH_QUERIES = [
    # ПСБ / Банковская деятельность
    "Пётр Фрадков Промсвязьбанк интервью 2025",
    "Пётр Фрадков ПСБ финансовые результаты",
    "Пётр Фрадков банк оборонный заказ",
    "ПСБ Фрадков цифровая трансформация",
    "Пётр Фрадков военная ипотека",
    "Пётр Фрадков ПСБ стратегия развитие",
    "Фрадков Промсвязьбанк государственный оборонный заказ 2025",
    "Пётр Фрадков ПСБ поддержка участников спецоперации",
    "ПСБ Фрадков Мишустин встреча",
    "Пётр Фрадков Промсвязьбанк Путин доклад",

    # ВФЛА / Спорт
    "Пётр Фрадков ВФЛА президент",
    "Пётр Фрадков лёгкая атлетика 2025",
    "ВФЛА Фрадков стратегия развитие",
    "Пётр Фрадков беговые центры",
    "Пётр Фрадков World Athletics",
    "Фрадков федерация лёгкой атлетики соревнования",
    "Пётр Фрадков ОКР олимпийский комитет",
    "ВФЛА Фрадков doping sanctions восстановление",

    # Экспорт (исторический + текущий)
    "Пётр Фрадков Российский экспортный центр",
    "Пётр Фрадков ЭКСАР экспортное страхование",
    "Фрадков несырьевой экспорт поддержка",
    "Пётр Фрадков БРИКС финансы",

    # Санкции / Международная деятельность
    "Пётр Фрадков санкции ЕС",
    "Пётр Фрадков санкции Великобритания",
    "Fradkov PSB sanctions",
    "Пётр Фрадков замминистра обороны",

    # Цифровые инновации
    "Пётр Фрадков цифровой рубль",
    "Пётр Фрадков блокчейн банк",
    "ПСБ Фрадков искусственный интеллект",
    "Фрадков финтех инновации",

    # Биография / Назначения
    "Пётр Михайлович Фрадков биография",
    "Пётр Фрадков назначение",
    "Пётр Фрадков карьера",
    "Пётр Фрадков награды",

    # Выступления / Форумы
    "Пётр Фрадков ПМЭФ выступление",
    "Пётр Фрадков форум ВТБ",
    "Пётр Фрадков пресс-конференция",
    "Пётр Фрадков интервью РБК",
    "Пётр Фрадков интервью Коммерсантъ",

    # Правительство / Госструктуры
    "Пётр Фрадков Министерство обороны",
    "Пётр Фрадков государственные программы",
    "Фрадков региональные встречи губернаторы",
]


# ══════════════════════════════════════════════════════════════════════
# SEARCH & PARSE
# ══════════════════════════════════════════════════════════════════════

def search_yandex(query, page=0):
    """Поиск через Yandex Search API v2 (rawData XML)."""
    global IAM_TOKEN
    try:
        headers = {
            "Authorization": f"Bearer {IAM_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": {
                "search_type": "SEARCH_TYPE_RU",
                "query_text": query,
                "page": page
            },
            "folder_id": FOLDER_ID,
            "max_passages": 5
        }
        resp = requests.post(YANDEX_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 401:
            # Токен истёк — обновляем
            new_token = get_iam_token()
            if new_token:
                IAM_TOKEN = new_token
                headers["Authorization"] = f"Bearer {IAM_TOKEN}"
                resp = requests.post(YANDEX_URL, headers=headers, json=payload, timeout=30)

        if resp.status_code != 200:
            return []

        data = resp.json()
        results = []

        # Парсим rawData (base64 XML)
        raw_b64 = data.get("rawData", "")
        if raw_b64:
            try:
                raw_xml = base64.b64decode(raw_b64).decode("utf-8", errors="ignore")
                root = ET.fromstring(raw_xml)

                for doc in root.findall(".//doc"):
                    url_elem = doc.find("url")
                    title_elem = doc.find("title")
                    passages = doc.findall(".//passage")

                    url = url_elem.text if url_elem is not None and url_elem.text else ""
                    title = title_elem.text if title_elem is not None and title_elem.text else ""

                    # Собираем текст из пассажей
                    passage_text = " ".join(
                        p.text for p in passages if p.text
                    )

                    if url and not url.startswith("https://yandex.ru/images"):
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": passage_text[:500] if passage_text else title,
                            "full_text": passage_text[:5000] if passage_text else "",
                            "query": query
                        })
            except Exception as e:
                print(f"  ✗ XML parse error: {e}")

        return results
    except Exception as e:
        print(f"  ✗ Search error: {e}")
        return []


def fetch_page(url):
    """Загружает страницу и извлекает текст."""
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        })
        if resp.status_code != 200:
            return ""

        # Simple HTML to text
        text = resp.text
        # Remove scripts, styles
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:10000]
    except:
        return ""


# ══════════════════════════════════════════════════════════════════════
# LLM (Ollama Cloud) — все LLM-вычисления в облаке
# ══════════════════════════════════════════════════════════════════════

def cloud_llm(prompt, max_tokens=500):
    """Вызов Ollama Cloud для LLM-задач."""
    try:
        resp = requests.post(OLLAMA_CLOUD_URL, headers=OLLAMA_CLOUD_HEADERS, json={
            "model": OLLAMA_CLOUD_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": max_tokens}
        }, timeout=60)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        return f"ERROR: {e}"


def extract_quotes_cloud(text, source_url=""):
    """Извлекает цитаты Фрадкова из текста через облачный LLM."""
    prompt = f"""Извлеки все цитаты и ключевые утверждения Петра Михайловича Фрадкова из текста.
Если в тексте нет цитат Фрадкова — верни пустой JSON массив.

Текст:
{text[:3000]}

Верни СТРОГО JSON массив:
[{{"text": "точная цитата или парафраз", "context": "контекст высказывания (1 строка)"}}]

ТОЛЬКО JSON массив. Если цитат нет — []."""

    result = cloud_llm(prompt, max_tokens=800)

    # Parse JSON
    try:
        if "```" in result:
            lines = result.split("\n")
            result = "\n".join(l for l in lines if not l.strip().startswith("```"))
        start = result.find("[")
        end = result.rfind("]") + 1
        if start >= 0 and end > start:
            quotes = json.loads(result[start:end])
            # Add source
            for q in quotes:
                q["source_url"] = source_url
                q["text"] = q.get("text", "")[:1000]
            return [q for q in quotes if len(q.get("text", "")) > 20]
    except:
        pass
    return []


def enrich_metadata_cloud(text, date=""):
    """Обогащает метаданные через облачный LLM."""
    prompt = f"""Проанализируй цитату. Ответь СТРОГО JSON:
Цитата: "{text[:300]}"
Дата: {date}
JSON: {{"topic": "тема 2-4 слова", "event": "событие или пусто", "persons_mentioned": ["люди/орг"], "key_concepts": ["3-5 концептов"]}}
ТОЛЬКО JSON."""

    result = cloud_llm(prompt, max_tokens=250)
    try:
        if "```" in result:
            lines = result.split("\n")
            result = "\n".join(l for l in lines if not l.strip().startswith("```"))
        start, end = result.find("{"), result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except:
        pass
    return {}


def extract_entities_cloud(text):
    """NER через облачный LLM."""
    prompt = f"""Из цитаты извлеки упомянутые сущности. Ответь СТРОГО JSON:
Цитата: "{text[:300]}"
JSON: {{"persons": ["люди"], "organizations": ["организации"], "events": ["события"], "places": ["места/страны"]}}
ТОЛЬКО JSON."""

    result = cloud_llm(prompt, max_tokens=200)
    try:
        if "```" in result:
            lines = result.split("\n")
            result = "\n".join(l for l in lines if not l.strip().startswith("```"))
        start, end = result.find("{"), result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except:
        pass
    return {}


# ══════════════════════════════════════════════════════════════════════
# EMBEDDINGS (local)
# ══════════════════════════════════════════════════════════════════════

def get_embedding(text):
    """Локальная векторизация."""
    try:
        resp = requests.post(OLLAMA_LOCAL_URL, json={
            "model": EMBEDDING_MODEL, "prompt": text
        }, timeout=60)
        resp.raise_for_status()
        return resp.json().get("embedding", [])
    except:
        return []


def cosine_sim(a, b):
    va, vb = np.array(a), np.array(b)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


# ══════════════════════════════════════════════════════════════════════
# STORAGE
# ══════════════════════════════════════════════════════════════════════

def load_to_qdrant(quotes_data):
    """Загружает цитаты в Qdrant."""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    points = []
    for qd in quotes_data:
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=qd["embedding"],
            payload={
                "quote_id": qd["quote_id"],
                "text": qd["text"][:1000],
                "text_full": qd["text"],
                "date": qd.get("date", ""),
                "year": int(qd["date"][:4]) if qd.get("date") and len(qd["date"]) >= 4 else None,
                "period": "autonomous_build",
                "cluster": None,
                "source_url": qd.get("source_url", ""),
                "topic": qd.get("topic", ""),
                "event": qd.get("event", ""),
                "persons_mentioned": qd.get("persons_mentioned", []),
                "key_concepts": qd.get("key_concepts", []),
                "node_type": "Quote"
            }
        ))
    if points:
        client.upsert(collection_name=COLLECTION, points=points)
    return len(points)


def load_to_neo4j(quotes_data):
    """Загружает цитаты и связи в Neo4j."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    with driver.session() as session:
        for qd in quotes_data:
            qid = qd["quote_id"]
            session.run("""
                MERGE (q:Quote {node_id: $qid})
                SET q.text = $text, q.date = $date, q.source_url = $url,
                    q.topic = $topic, q.event = $event,
                    q.persons_mentioned = $persons, q.key_concepts = $concepts,
                    q.period = 'autonomous_build', q.subject = 'petr_m_fradkov'
            """, qid=qid, text=qd["text"][:5000], date=qd.get("date", ""),
                url=qd.get("source_url", ""), topic=qd.get("topic", ""),
                event=qd.get("event", ""),
                persons=qd.get("persons_mentioned", []),
                concepts=qd.get("key_concepts", []))

            # Связь с Фрадковым
            session.run("""
                MATCH (p:Person {name: 'Фрадков, Пётр Михайлович'})
                MATCH (q:Quote {node_id: $qid})
                MERGE (p)-[:SAID]->(q)
            """, qid=qid)

            # NER сущности
            for cat, label, edge_type in [
                ("persons", "Person", "MENTIONS_PERSON"),
                ("organizations", "Organization", "MENTIONS_ORG"),
                ("events", "Event", "MENTIONS_EVENT"),
                ("places", "Place", "MENTIONS_PLACE"),
            ]:
                for entity in qd.get(f"ner_{cat}", []):
                    if entity and len(entity) > 1:
                        eid = f"ner_{cat}_{entity.lower().replace(' ', '_')[:50]}"
                        session.run(f"""
                            MERGE (e:{label} {{node_id: $eid}})
                            SET e.name = $name, e.source = 'autonomous_ner'
                            WITH e
                            MATCH (q:Quote {{node_id: $qid}})
                            MERGE (q)-[:{edge_type}]->(e)
                        """, eid=eid, name=entity, qid=qid)

    driver.close()


def find_semantic_links(embedding, exclude_id):
    """Находит семантически близкие цитаты в Qdrant."""
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    results = client.query_points(
        collection_name=COLLECTION,
        query=embedding,
        limit=10
    )
    links = []
    for r in results.points:
        qid = r.payload.get("quote_id", "")
        if qid != exclude_id and r.score >= 0.75:
            links.append({"quote_id": qid, "similarity": round(r.score, 4)})
            # Add edge to Neo4j
            try:
                driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
                with driver.session() as session:
                    session.run("""
                        MATCH (a:Quote {node_id: $from_id})
                        MATCH (b:Quote {node_id: $to_id})
                        MERGE (a)-[r:SEMANTICALLY_RELATED]->(b)
                        SET r.similarity = $sim
                    """, from_id=exclude_id, to_id=qid, sim=round(r.score, 4))
                driver.close()
            except:
                pass
    return links


# ══════════════════════════════════════════════════════════════════════
# QUALITY CHECK
# ══════════════════════════════════════════════════════════════════════

def quality_check(new_quotes):
    """Проверяет качество загруженных цитат."""
    issues = []

    for q in new_quotes:
        text = q.get("text", "")

        # Проверка 1: длина
        if len(text) < 30:
            issues.append(f"Слишком короткая: {text[:50]}")

        # Проверка 2: содержит ли имя Фрадкова
        text_lower = text.lower()
        if not any(kw in text_lower for kw in ["фрадков", "псб", "вфла", "промсвязьбанк", "он", "мы"]):
            issues.append(f"Возможно не про Фрадкова: {text[:80]}")

        # Проверка 3: дубликат?
        text_hash = hashlib.md5(text.encode()).hexdigest()
        q["_hash"] = text_hash

    # Проверка дубликатов
    hashes = [q.get("_hash") for q in new_quotes]
    dupes = len(hashes) - len(set(hashes))
    if dupes > 0:
        issues.append(f"Дубликатов: {dupes}")

    return issues


def get_graph_stats():
    """Текущая статистика графа."""
    qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    info = qdrant.get_collection(COLLECTION)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    with driver.session() as session:
        nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        edges = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
    driver.close()

    return {
        "qdrant_points": info.points_count,
        "neo4j_nodes": nodes,
        "neo4j_edges": edges
    }


# ══════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════════════════════════

def safe_save(path, data):
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".json.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except:
        os.unlink(tmp_path)
        raise


def autonomous_build():
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + "  АВТОНОМНОЕ СТРОИТЕЛЬСТВО ВЕКТОРНО-ГРАФОВОГО ПРОСТРАНСТВА".center(68) + "║")
    print("║" + "  LLM: Ollama Cloud | Embeddings: local | Storage: Qdrant+Neo4j".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    # Начальная статистика
    stats = get_graph_stats()
    print(f"Начальное состояние:")
    print(f"  Qdrant: {stats['qdrant_points']} точек")
    print(f"  Neo4j: {stats['neo4j_nodes']} узлов, {stats['neo4j_edges']} рёбер")
    print(f"  Запросов: {len(SEARCH_QUERIES)}")
    print()

    seen_urls = set()
    seen_texts = set()
    total_new_quotes = 0
    total_iterations = 0
    no_new_count = 0

    # Загружаем граф для обновления
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    for iteration in range(1, 101):  # Макс 100 итераций
        total_iterations = iteration
        print(f"{'='*60}")
        print(f"ИТЕРАЦИЯ {iteration} / {len(SEARCH_QUERIES)} запросов")
        print(f"{'='*60}")

        new_in_iteration = 0
        queries_this_round = SEARCH_QUERIES[:min(5, len(SEARCH_QUERIES))]
        # Ротируем запросы
        start_idx = (iteration - 1) * 5 % len(SEARCH_QUERIES)
        queries_this_round = []
        for i in range(5):
            idx = (start_idx + i) % len(SEARCH_QUERIES)
            queries_this_round.append(SEARCH_QUERIES[idx])

        for qi, query in enumerate(queries_this_round):
            print(f"\n  [{qi+1}/5] Поиск: {query}")

            # Поиск
            results = search_yandex(query)
            new_results = [r for r in results if r["url"] not in seen_urls]
            for r in results:
                seen_urls.add(r["url"])

            if not new_results:
                print(f"    Новых результатов: 0")
                continue

            print(f"    Новых результатов: {len(new_results)}")

            for ri, result in enumerate(new_results[:3]):  # Макс 3 страницы за запрос
                url = result["url"]
                text = result.get("full_text", "")

                # Если текста мало — загружаем страницу
                if len(text) < 200:
                    text = fetch_page(url)

                if len(text) < 100:
                    continue

                # Извлечение цитат через облачный LLM
                quotes = extract_quotes_cloud(text, url)

                if not quotes:
                    continue

                # Фильтрация дубликатов
                unique_quotes = []
                for q in quotes:
                    qt = q.get("text", "")
                    qt_hash = hashlib.md5(qt.encode()).hexdigest()
                    if qt_hash not in seen_texts:
                        seen_texts.add(qt_hash)
                        unique_quotes.append(q)

                if not unique_quotes:
                    continue

                print(f"    Стр. {ri+1}: {len(unique_quotes)} новых цитат")

                # Обработка каждой цитаты
                quotes_data = []
                for q in unique_quotes:
                    qt = q["text"]

                    # Векторизация (локально)
                    embedding = get_embedding(qt)
                    if not embedding:
                        continue

                    # Обогащение метаданных (облако)
                    meta = enrich_metadata_cloud(qt)

                    # NER (облако)
                    entities = extract_entities_cloud(qt)

                    qd = {
                        "quote_id": f"auto_{uuid.uuid4().hex[:12]}",
                        "text": qt,
                        "embedding": embedding,
                        "source_url": q.get("source_url", url),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "topic": meta.get("topic", ""),
                        "event": meta.get("event", ""),
                        "persons_mentioned": meta.get("persons_mentioned", []),
                        "key_concepts": meta.get("key_concepts", []),
                        "ner_persons": entities.get("persons", []),
                        "ner_organizations": entities.get("organizations", []),
                        "ner_events": entities.get("events", []),
                        "ner_places": entities.get("places", []),
                    }
                    quotes_data.append(qd)

                if not quotes_data:
                    continue

                # Проверка качества
                issues = quality_check(quotes_data)
                if issues:
                    print(f"    ⚠ Качество: {', '.join(issues[:3])}")

                # Загрузка в Qdrant
                loaded_q = load_to_qdrant(quotes_data)

                # Загрузка в Neo4j
                load_to_neo4j(quotes_data)

                # Семантические связи
                for qd in quotes_data:
                    links = find_semantic_links(qd["embedding"], qd["quote_id"])

                new_in_iteration += len(quotes_data)
                total_new_quotes += len(quotes_data)

                print(f"    ✓ Загружено: {len(quotes_data)} цитат")

        # Ротация запросов
        SEARCH_QUERIES.append(SEARCH_QUERIES.pop(0))

        # Обновляем IAM-токен каждые 5 итераций
        if iteration % 5 == 0:
            new_token = get_iam_token()
            if new_token:
                global IAM_TOKEN
                IAM_TOKEN = new_token

        # Статистика итерации
        stats = get_graph_stats()
        print(f"\n  Итог итерации {iteration}:")
        print(f"    Новых цитат: {new_in_iteration}")
        print(f"    Всего новых: {total_new_quotes}")
        print(f"    Qdrant: {stats['qdrant_points']}")
        print(f"    Neo4j: {stats['neo4j_nodes']} узлов, {stats['neo4j_edges']} рёбер")

        # Сохраняем граф
        graph["metadata"]["autonomous_build"] = {
            "iteration": iteration,
            "total_new_quotes": total_new_quotes,
            "last_update": datetime.now().isoformat(),
            "stats": stats
        }
        safe_save(GRAPH_PATH, graph)

        # Условие остановки
        if new_in_iteration == 0:
            no_new_count += 1
            print(f"    Нет новых данных ({no_new_count}/3)")
            if no_new_count >= 3:
                print("\n  ✓ Информация исчерпана. Остановка.")
                break
        else:
            no_new_count = 0

    # Финальный отчёт
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + "  СТРОИТЕЛЬСТВО ЗАВЕРШЕНО".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print(f"Итераций: {total_iterations}")
    print(f"Новых цитат: {total_new_quotes}")
    print(f"URL обработано: {len(seen_urls)}")

    stats = get_graph_stats()
    print(f"\nФинальное состояние:")
    print(f"  Qdrant: {stats['qdrant_points']} точек")
    print(f"  Neo4j: {stats['neo4j_nodes']} узлов, {stats['neo4j_edges']} рёбер")
    print()
    print("✓ Векторно-графовое пространство обогащено")


if __name__ == "__main__":
    autonomous_build()

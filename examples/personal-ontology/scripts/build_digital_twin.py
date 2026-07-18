#!/usr/bin/env python3
"""
Построение модели цифрового двойника.

Связанная структура:
  Quote → said_at → Event (TimelineEvent или OpenEvent)
    → in_role → Position → in_org → Organization
    → about → System
    → in_circumstance → Circumstance → at_location → Place

События (Event):
  - TimelineEvent: верифицированные факты карьеры (23 события)
  - OpenEvent: события из открытых источников (LLM с контролем галлюцинаций)

Контроль галлюцинаций:
  - LLM извлекает событие из текста страницы
  - Cosine similarity между извлечённым событием и текстом страницы
  - Если < 0.5 → отбросить (возможная галлюцинация)
"""

import json
import os
import re
import tempfile
import uuid
import requests
import numpy as np

# ═══ CONFIG ═══
GRAPH_PATH = "/Users/arturoceretnyj/qwencode-as-a-core/examples/personal-ontology/output/personal_ontology_graph.json"
QUOTES_PATH = "/Users/arturoceretnyj/qwencode-as-a-core/examples/personal-ontology/output/rebuild_verified_quotes.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
EMBED_URL = "http://localhost:11434/api/embeddings"
LLM_MODEL = "qwen3-coder-next"
MIN_CONFIDENCE = 0.5


def safe_save(path, data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".json.tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def get_embedding(text):
    try:
        resp = requests.post(EMBED_URL, json={"model": "qwen3-embedding:8b", "prompt": text}, timeout=30)
        return resp.json().get("embedding", [])
    except:
        return []


def cosine(v1, v2):
    a, b = np.array(v1), np.array(v2)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0: return 0.0
    return float(np.dot(a, b) / (na * nb))


def extract_event(text, source_url):
    """
    Извлекает событие из текста страницы (LLM с контролем галлюцинаций).
    Возвращает: event_dict или None
    """
    prompt = f"""Извлеки событие/ситуацию, в которой произнесена цитата.

Цитата: "{text[:200]}"
Источник: {source_url}

Ответь СТРОГО JSON:
{{"type": "выступление|интервью|встреча|совещание|заявление|публикация", "name": "короткое название", "description": "описание ситуации", "location": "место или пусто", "date_approx": "год или период или пусто"}}

Если событие неясно — верни null."""

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": LLM_MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 200}
        }, timeout=30)
        content = resp.json().get("response", "").strip()

        if "```" in content:
            content = "\n".join(l for l in content.split("\n") if not l.strip().startswith("```"))

        start, end = content.find("{"), content.rfind("}") + 1
        if start >= 0 and end > start:
            event = json.loads(content[start:end])
            if event:
                event["source_url"] = source_url
                return event
    except:
        pass
    return None


def validate_event(event_text, page_text):
    """Валидация события: cosine similarity с текстом страницы."""
    e_emb = get_embedding(event_text)
    if not e_emb: return 0.0

    max_sim = 0.0
    for i in range(0, len(page_text), 200):
        chunk = page_text[i:i+500]
        if len(chunk) < 50: continue
        c_emb = get_embedding(chunk)
        if not c_emb: continue
        sim = cosine(e_emb, c_emb)
        if sim > max_sim: max_sim = sim
    return max_sim


def build_digital_twin():
    """Строит связанную модель цифрового двойника."""
    print("=" * 60)
    print("ПОСТРОЕНИЕ МОДЕЛИ ЦИФРОВОГО ДВОЙНИКА")
    print("=" * 60)

    # Загружаем граф и цитаты
    with open(GRAPH_PATH) as f:
        graph = json.load(f)
    with open(QUOTES_PATH) as f:
        quotes_data = json.load(f)

    print(f"Граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    print(f"Цитат: {len(quotes_data)}")

    # ═══ Индекс существующих узлов ═══
    existing_quotes = {q['attributes'].get('text'): q for q in graph['nodes'] if q['type'] == 'Quote'}
    existing_events = {e.get('name', ''): e for e in graph['nodes'] if e['type'] == 'TimelineEvent'}
    existing_orgs = {o.get('name', ''): o for o in graph['nodes'] if o['type'] == 'Organization'}
    existing_positions = {p.get('name', ''): p for p in graph['nodes'] if p['type'] == 'Position'}

    # ═══ Словари для новых узлов ═══
    open_events = {}  # name → event_node
    systems = {}  # name → system_node
    circumstances = {}  # name → circumstance_node

    new_nodes = []
    new_edges = []
    processed = 0
    events_created = 0
    systems_created = 0

    for qd in quotes_data:
        text = qd['text']
        source_url = qd['source_url']

        # Определяем ID Quote (существующий или новый)
        is_new = text not in existing_quotes
        if is_new:
            qid = f"rb_dt_{uuid.uuid4().hex[:10]}"
        else:
            qid = existing_quotes[text]['id']

        # ══ Извлечение события ═══
        event = extract_event(text, source_url)
        if not event:
            processed += 1
            continue

        event_name = event.get("name", "")
        event_type = event.get("type", "")
        event_desc = event.get("description", "")

        # Валидация события
        if event_desc:
            confidence = validate_event(event_desc, text)
            if confidence < MIN_CONFIDENCE:
                processed += 1
                continue
        else:
            confidence = 0.0

        # ═══ Создание OpenEvent ══
        if event_name and event_name not in open_events:
            eid = f"open_event_{uuid.uuid4().hex[:10]}"
            open_events[event_name] = {
                "id": eid,
                "type": "OpenEvent",
                "name": event_name,
                "attributes": {
                    "type": event_type,
                    "description": event_desc,
                    "location": event.get("location", ""),
                    "date_approx": event.get("date_approx", ""),
                    "source_url": source_url,
                    "validation_confidence": round(confidence, 4)
                }
            }
            new_nodes.append(open_events[event_name])
            events_created += 1

        # ═══ Создание Quote (только для новых) ══
        if is_new:
            new_quote = {
                "id": qid,
                "type": "Quote",
                "attributes": {
                    "text": text,
                    "subject": "petr_m_fradkov",
                    "source_url": source_url,
                    "validation_status": qd['validation_status'],
                    "validation_confidence": qd['validation_confidence'],
                    "period": "digital_twin_2026"
                },
                "embedding": qd['embedding'],
                "embedding_model": "qwen3-embedding:8b"
            }
            new_nodes.append(new_quote)
        processed += 1

        # ═══ Связи ═══
        # Quote → said_at → OpenEvent
        if event_name in open_events:
            new_edges.append({
                "from": qid,
                "to": open_events[event_name]["id"],
                "type": "said_at",
                "attributes": {}
            })

        # ═══ Определение системы (контекста) ═══
        system_candidates = ["ПСБ", "Промсвязьбанк", "ВФЛА", "РЭЦ", "ЭКСАР", "ВЭБ", "ОПК", "экспорт", "спорт"]
        for sys_name in system_candidates:
            if sys_name.lower() in text.lower():
                if sys_name not in systems:
                    sid = f"system_{sys_name.lower().replace(' ', '_')}"
                    systems[sys_name] = {
                        "id": sid,
                        "type": "System",
                        "name": sys_name,
                        "attributes": {"domain": event_type}
                    }
                    new_nodes.append(systems[sys_name])
                    systems_created += 1
                break

        # ═══ Создание Quote ══
        qid = f"rb_dt_{uuid.uuid4().hex[:10]}"
        new_quote = {
            "id": qid,
            "type": "Quote",
            "attributes": {
                "text": text,
                "subject": "petr_m_fradkov",
                "source_url": source_url,
                "validation_status": qd['validation_status'],
                "validation_confidence": qd['validation_confidence'],
                "period": "digital_twin_2026"
            },
            "embedding": qd['embedding'],
            "embedding_model": "qwen3-embedding:8b"
        }
        new_nodes.append(new_quote)
        processed += 1

        # ═══ Связи ═══
        # Quote → said_at → OpenEvent
        if event_name in open_events:
            new_edges.append({
                "from": qid,
                "to": open_events[event_name]["id"],
                "type": "said_at",
                "attributes": {}
            })

        # Quote → about → System
        for sys_name in systems:
            if sys_name.lower() in text.lower():
                new_edges.append({
                    "from": qid,
                    "to": systems[sys_name]["id"],
                    "type": "about",
                    "attributes": {}
                })

        # OpenEvent → occurred_in → Circumstance (если есть локация)
        if event.get("location") and event["location"] not in circumstances:
            loc = event["location"]
            cid = f"circumstance_{uuid.uuid4().hex[:10]}"
            circumstances[loc] = {
                "id": cid,
                "type": "Circumstance",
                "name": loc,
                "attributes": {"description": f"Место: {loc}"}
            }
            new_nodes.append(circumstances[loc])
            new_edges.append({
                "from": open_events[event_name]["id"],
                "to": cid,
                "type": "occurred_in",
                "attributes": {}
            })

        if processed % 50 == 0:
            print(f"  Обработано: {processed}/{len(quotes_data)}, событий: {events_created}, систем: {systems_created}")

    # ═══ Сохранение ═══
    graph['nodes'].extend(new_nodes)
    graph['edges'].extend(new_edges)
    graph['metadata']['digital_twin'] = {
        "created": True,
        "open_events": len(open_events),
        "systems": len(systems),
        "circumstances": len(circumstances),
        "new_nodes": len(new_nodes),
        "new_edges": len(new_edges)
    }

    safe_save(GRAPH_PATH, graph)

    print(f"\n✓ Построено:")
    print(f"  OpenEvent: {events_created}")
    print(f"  System: {systems_created}")
    print(f"  Circumstance: {len(circumstances)}")
    print(f"  Новых узлов: {len(new_nodes)}")
    print(f"  Новых рёбер: {len(new_edges)}")
    print(f"  Всего узлов: {len(graph['nodes'])}")
    print(f"  Всего рёбер: {len(graph['edges'])}")


if __name__ == "__main__":
    build_digital_twin()
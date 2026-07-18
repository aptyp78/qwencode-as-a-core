#!/usr/bin/env python3
"""
Генерация поисковых запросов из конфигурации субъекта.

Принимает: config/subject.yaml
Возвращает: output/queries.json (60+ запросов)

Использует: локальный LLM (qwen3-coder-next) для генерации запросов
"""

import json
import os
import yaml
import requests

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "subject.yaml")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "output", "queries.json")
OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "qwen3-coder-next"


def load_config():
    """Загружает конфигурацию субъекта."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def generate_queries(config, count=60):
    """Генерирует поисковые запросы через LLM."""
    subject = config['subject']

    # Формируем контекст
    roles = ", ".join(subject.get('current_roles', []) + subject.get('past_roles', []))
    domains = ", ".join(subject.get('domains', []))
    orgs = ", ".join(subject.get('organizations', []))
    keywords = ", ".join(subject.get('keywords', []))

    prompt = f"""Сгенерируй {count} поисковых запросов на русском языке для сбора информации о человеке.

Субъект: {subject['name']}
Роли: {roles}
Домены: {domains}
Организации: {orgs}
Ключевые слова: {keywords}
Периоды: {subject.get('time_periods', {}).get('current', '2018-2026')}

Запросы должны охватывать:
- Выступления и интервью (что говорит, где, когда)
- Решения и действия (что делает в каждой роли)
- События (ПМЭФ, совещания, встречи)
- Контексты (ситуации, обстоятельства)

Верни СТРОГО JSON массив строк. Каждая строка — один поисковый запрос.

Примеры хорошего запроса:
- "{subject['name']} ПМЭФ 2025 выступление"
- "{subject['name']} интервью 2024"
- "{subject['organizations'][0]} {subject['keywords'][0]}"

JSON: ["запрос 1", "запрос 2", ...]"""

    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": LLM_MODEL, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.2, "num_predict": 800}
        }, timeout=300)
        content = resp.json().get("response", "").strip()

        if "```" in content:
            content = "\n".join(l for l in content.split("\n") if not l.strip().startswith("```"))

        start, end = content.find("["), content.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
    except Exception as e:
        print(f"Ошибка генерации: {e}")

    return []


def add_template_queries(config, generated):
    """Добавляет шаблонные запросы для гарантированного покрытия."""
    subject = config['subject']
    name = subject['name']
    templates = []

    # По годам
    for year in range(2026, 2017, -1):
        templates.append(f"{name} {year}")
        templates.append(f"{name} {year} интервью")

    # По организациям
    for org in subject.get('organizations', [])[:5]:
        templates.append(f"{name} {org}")

    # По ключевым словам
    for kw in subject.get('keywords', [])[:5]:
        templates.append(f"{name} {kw}")

    # Дедупликация
    existing = set(generated)
    unique = [q for q in templates if q not in existing]

    return generated + unique[:max(0, 60 - len(generated))]


def main():
    print("=" * 60)
    print("ГЕНЕРАЦИЯ ПОИСКОВЫХ ЗАПРОСОВ")
    print("=" * 60)

    config = load_config()
    subject = config['subject']
    print(f"Субъект: {subject['name']}")
    print(f"Ролей: {len(subject.get('current_roles', [])) + len(subject.get('past_roles', []))}")
    print(f"Доменов: {len(subject.get('domains', []))}")
    print(f"Организаций: {len(subject.get('organizations', []))}")
    print()

    # Генерация через LLM
    print("Генерация через LLM...")
    generated = generate_queries(config, count=40)
    print(f"  Сгенерировано: {len(generated)}")

    # Добавление шаблонов
    print("Добавление шаблонных запросов...")
    queries = add_template_queries(config, generated)
    print(f"  Всего: {len(queries)}")

    # Сохранение
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(queries, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Сохранено: {OUTPUT_PATH}")
    print(f"  Запросов: {len(queries)}")
    print("\nПримеры:")
    for q in queries[:5]:
        print(f"  - {q}")


if __name__ == "__main__":
    main()
# Fradkov Ontology — Production Stack

Векторно-графовое пространство цифровой тени Фрадкова П.М.
Инструмент стохастического сопоставления новых документов с известным контекстом деятельности.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│  Query API (FastAPI, port 8000)                              │
│  POST /query — стохастическое сопоставление                  │
│  POST /ingest — загрузка нового документа                    │
│  GET /stats, /clusters, /transitions                         │
├─────────────────────────────────────────────────────────────┤
│  Qdrant (port 6333)          │  Neo4j (port 7474/7687)      │
│  1378+ векторов (4096d)      │  1461 узел, 3421 ребро       │
│  Cosine similarity search    │  Граф связей + Cypher queries │
├─────────────────────────────────────────────────────────────┤
│  Ollama (port 11434)                                         │
│  qwen3-embedding:8b — векторизация (локально)               │
│  qwen3-coder-next — обогащение (локально/Ollama Cloud)      │
└─────────────────────────────────────────────────────────────┘
```

## Быстрый старт

```bash
# Запуск всего стека
./start.sh

# Или по шагам:
docker compose up -d                          # Qdrant + Neo4j
source venv/bin/activate
python scripts/migrate_to_qdrant.py           # Миграция векторов
python scripts/migrate_to_neo4j.py            # Миграция графа
python scripts/query_api.py                   # API-сервер
```

## Использование

### Стохастическое сопоставление
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"text": "Цифровой рубль и суверенная платёжная инфраструктура"}'
```

### Загрузка нового документа
```bash
# Из текста
python scripts/ingest_document.py --text "Текст цитаты..." --date 2026-07-15

# Из файла
python scripts/ingest_document.py --file document.txt --source https://...

# Из URL
python scripts/ingest_document.py --url https://example.com/article
```

### Swagger UI
Откройте http://localhost:8000/docs

## Структура

```
fradkov-ontology/
├── docker-compose.yml          # Qdrant + Neo4j
├── start.sh                    # Запуск стека
├── requirements.txt            # Python-зависимости
├── data/                       # Исходные данные
│   ├── fradkov_all_real_quotes.json
│   └── fradkov_historical_quotes.json
├── output/                     # Граф (JSON)
│   └── fradkov_ontology_stochastic.json
├── scripts/
│   ├── migrate_to_qdrant.py    # JSON → Qdrant
│   ├── migrate_to_neo4j.py     # JSON → Neo4j
│   ├── query_api.py            # FastAPI сервер
│   ├── ingest_document.py      # Загрузка документов
│   ├── phase1_1_and_1_2.py     # Векторизация (фаза 1)
│   ├── phase2_historical_parsing.py
│   ├── phase3_stochastic_layer.py
│   └── vectorize_historical_and_connect.py
├── docs/
│   └── GRAPH_PURPOSE.md
└── venv/                       # Python venv
```

## Данные

| Метрика | Значение |
|---------|----------|
| Реальных высказываний | 1379+ |
| Покрытие | 2000-2026 (27 лет) |
| Семантических связей | 1929+ |
| Кластеров (K-means) | 20 |
| Вероятностных рёбер | 30 |
| Типов узлов | 10 (Person, Quote, Organization, ...) |
| Типов рёбер | 11 (SAID, SEMANTICALLY_RELATED, ...) |

## Принципы

1. **Суверенность** — все вычисления локальные, air-gap capable
2. **Реальность данных** — только реальные высказывания из открытых источников
3. **Векторно-графовая природа** — семантика (embeddings) + структура (граф)
4. **Стохастичность** — вероятностные связи, матрицы переходов
5. **Доказуемость** — каждое высказывание traceable до источника
6. **Инкрементальное обогащение** — каждый новый документ обогащает граф

#!/bin/bash
# Fradkov Ontology — запуск production-стека
# Qdrant + Neo4j + Query API

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Fradkov Ontology — Production Stack                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# 1. Docker containers
echo "[1/3] Запуск Qdrant + Neo4j..."
docker compose up -d
echo "  ✓ Контейнеры запущены"
echo ""

# 2. Ждём готовности
echo "[2/3] Ожидание готовности сервисов..."
for i in $(seq 1 30); do
    if curl -s http://localhost:6333/healthz > /dev/null 2>&1; then
        echo "  ✓ Qdrant готов"
        break
    fi
    sleep 1
done

for i in $(seq 1 30); do
    if curl -s -o /dev/null http://localhost:7474 2>/dev/null; then
        echo "  ✓ Neo4j готов"
        break
    fi
    sleep 1
done
echo ""

# 3. Ollama check
echo "[3/3] Проверка Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  ✓ Ollama локально доступен"
else
    echo "  ⚠ Ollama не запущен — запустите: ollama serve"
fi
echo ""

# 4. API
echo "Запуск Query API..."
echo "  Swagger UI: http://localhost:8000/docs"
echo "  Neo4j Browser: http://localhost:7474 (neo4j / personal2026)"
echo ""

source venv/bin/activate
exec python scripts/query_api.py

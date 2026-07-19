# Personal Ontology — Makefile
# One-click запуск инфраструктуры

.PHONY: config build validate serve clean help

help: ## Показать справку
	@echo "Personal Ontology — цели:"
	@echo ""
	@echo "  make config    — генерация запросов из config/subject.yaml"
	@echo "  make build     — полный цикл сбора (search → extract → validate → store)"
	@echo "  make validate  — валидация порога на выборке 50 URL"
	@echo "  make serve     — запуск Query API (port 8000)"
	@echo "  make clean     — очистка кэша и временных файлов"
	@echo ""

config: ## Генерация запросов из subject.yaml
	cd examples/personal-ontology && \
	source venv/bin/activate && \
	python scripts/generate_queries.py

build: ## Полный цикл сбора
	cd examples/personal-ontology && \
	source venv/bin/activate && \
	python scripts/rebuild_pipeline.py

validate: ## Валидация порога на выборке 50 URL
	cd examples/personal-ontology && \
	source venv/bin/activate && \
	python scripts/validate_threshold.py

serve: ## Запуск Query API
	cd examples/personal-ontology && \
	source venv/bin/activate && \
	python scripts/query_api.py

clean: ## Очистка кэша и временных файлов
	rm -rf ~/.personal-ontology/yandex_token.json
	rm -rf ~/.personal-ontology/embeddings_cache.json
	rm -rf examples/personal-ontology/output/expanded_queries.json
	rm -rf examples/personal-ontology/output/rebuild_verified_quotes.json
	@echo "✓ Кэш очищен"

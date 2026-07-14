# Архитектура QwenCode as a Core

## Гипотеза

`@qwen-code/qwen-code-core` можно использовать как встраиваемую библиотеку для построения специализированных AI-приложений, не ограничиваясь CLI-агентом.

## Проверка гипотезы

### Фаза 1: Базовая интеграция
- [ ] Установить `@qwen-code/qwen-code-core` как зависимость
- [ ] Импортировать `AgentCore` и `CoreToolScheduler`
- [ ] Запустить простой agent loop с одним tool

### Фаза 2: Custom tools
- [ ] Реализовать `pdf_normalizer` как qwen-code tool
- [ ] Реализовать `domain_analyzer` как qwen-code tool
- [ ] Реализовать `reflector` как qwen-code tool
- [ ] Проверить: agent loop корректно вызывает custom tools

### Фаза 3: End-to-end тест
- [ ] Подать PDF-документ → получить Universal Representation → определить домен
- [ ] Сравнить с MAS-оркестратором на Python (качество, скорость)

### Фаза 4: Масштабирование
- [ ] Batch-обработка N документов
- [ ] Parallel execution (ThreadPool / Worker Pool)
- [ ] Memory / RAG для накопления знаний

## Критерии успеха

| Критерий | Порог |
|----------|-------|
| Agent loop работает без модификации core | ✅ |
| Custom tools вызываются корректно | ✅ |
| End-to-end тест проходит на тестовых документах | ✅ |
| Производительность не хуже Python-версии | TBD |

## Риски

1. **TypeScript vs Python** — AI Canvas на Python, qwen-code на TypeScript. Возможны проблемы интеграции.
2. **API стабильность** — `@qwen-code/qwen-code-core` может менять API между версиями.
3. **Производительность** — Node.js vs Python — нужно тестировать.

## Альтернативы

Если гипотеза не подтвердится:
- Написать свой agent loop на Python (скопировать паттерны из qwen-code)
- Использовать `qwen serve` как daemon и общаться через HTTP API

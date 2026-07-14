# QwenCode as a Core

Экспериментальный проект по использованию `@qwen-code/qwen-code-core` как ядра для AI Canvas — суверенной среды анализа документов для C-level руководителей.

## Цель

Исследовать возможность использования qwen-code не как отдельного CLI-агента, а как **встраиваемой библиотеки** для построения специализированных AI-приложений.

## Архитектура

```
┌─────────────────────────────────────────┐
│  AI Canvas UI (CLI / Web / Bot)         │
├─────────────────────────────────────────┤
│  @qwen-code/qwen-code-core              │
│  ├── AgentCore (agent loop)             │
│  ├── CoreToolScheduler (tool dispatch)  │
│  ├── MemoryManager (RAG)                │
│  └── PermissionManager (approval)       │
├─────────────────────────────────────────┤
│  Custom Tools                           │
│  ├── pdf_normalizer                     │
│  ├── domain_analyzer                    │
│  └── reflector                          │
└─────────────────────────────────────────┘
```

## Что мы берём из qwen-code

- **Agent loop** — LLM call → tool detection → tool execution → result → next LLM call
- **Tool dispatch** — управление вызовами инструментов, retry, error handling
- **Memory / RAG** — индексация и поиск по контексту
- **Permission management** — approval pipeline (plan/default/auto-edit/auto/yolo)

## Что мы пишем сами

- **Custom tools** — специализированные инструменты для парсинга документов
- **UI** — интерфейс пользователя (CLI, веб, Telegram-бот)
- **Business logic** — доменная логика AI Canvas

## Установка

```bash
npm install
```

## Использование

```bash
npm start
```

## Структура проекта

```
qwencode-as-a-core/
├── src/
│   ├── index.ts              # Точка входа
│   ├── tools/                # Custom tools
│   │   ├── pdf_normalizer.ts
│   │   ├── domain_analyzer.ts
│   │   └── reflector.ts
│   └── ui/                   # Интерфейс пользователя
│       ├── cli.ts
│       └── web.ts
├── tests/
│   └── tools.test.ts
├── docs/
│   ├── architecture.md
│   └── api.md
├── package.json
├── tsconfig.json
├── .gitignore
└── LICENSE
```

## Технологии

- **TypeScript** — язык проекта
- **@qwen-code/qwen-code-core** — ядро agent loop
- **Node.js** — runtime
- **Ollama** — локальный инференс моделей (qwen3-coder-next, qwen3-vl:30b)

## Лицензия

Apache-2.0 — как и qwen-code.

## Связь с AI Canvas

Этот проект — **параллельный эксперимент** к основному MAS-оркестратору на Python. Цель: понять, можно ли использовать qwen-code как готовый agent loop для AI Canvas, или лучше написать свой на Python.

## Статус

🚧 **Экспериментальная стадия** — проверка гипотезы о встраиваемости qwen-code.

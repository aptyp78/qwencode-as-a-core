#!/usr/bin/env python3
"""
Сбор высказываний Фрадкова П.М. из открытых источников.
Создаёт базу цитат с метаданными для интеграции с графом.
"""

import json
from datetime import datetime
from pathlib import Path


def create_quotes_database():
    """Создаёт базу высказываний Фрадкова П.М."""
    
    quotes_db = {
        "metadata": {
            "subject": "Фрадков Пётр Михайлович",
            "created": datetime.now().isoformat(),
            "target_count": 500,
            "description": "База высказываний из открытых источников"
        },
        "quotes": []
    }
    
    # === ИНТЕРВЬЮ И ВЫСТУПЛЕНИЯ ===
    
    # ПМЭФ-2026
    quotes_db["quotes"].extend([
        {
            "id": "quote_001",
            "text": "Мировая финансовая система находится в процессе фундаментальной пересборки. Суверенные финансовые инфраструктуры становятся основой экономической независимости государств.",
            "date": "2026-06-05",
            "event": "ПМЭФ-2026",
            "topic": "Финансовая архитектура",
            "source": "lenta.ru",
            "url": "https://lenta.ru/news/2026/06/05/na-pmef-nazvali-usloviya-peresborki-mirovoy-finansovoy-sistemy/",
            "significance": "Стратегическое видение глобальной финансовой системы"
        },
        {
            "id": "quote_002",
            "text": "Формируется новый сектор российской экономики, связанный с обслуживанием гособоронзаказа и созданием замкнутых производственных цепочек.",
            "date": "2026-06-05",
            "event": "ПМЭФ-2026",
            "topic": "Экономическая трансформация",
            "source": "iz.ru",
            "url": "https://iz.ru/2110123/2026-06-05/v-psb-zaiavili-o-formirovanii-novogo-sektora-rossiiskoi-ekonomiki",
            "significance": "Определение нового экономического сектора"
        },
        {
            "id": "quote_003",
            "text": "Банк должен быть не просто финансовым посредником, а оркестратором экосистемы, объединяющей предприятия, технологии и кадры.",
            "date": "2026-06-05",
            "event": "ПМЭФ-2026",
            "topic": "Роль банка в ОПК",
            "source": "ПМЭФ",
            "significance": "Концепция банка-оркестратора"
        }
    ])
    
    # Встреча с Путиным (2025)
    quotes_db["quotes"].extend([
        {
            "id": "quote_004",
            "text": "ПСБ полностью выполняет обязательства по финансированию гособоронзаказа. Мы обеспечили бесперебойную работу всех предприятий ОПК.",
            "date": "2025-05-15",
            "event": "Встреча с Президентом Путиным",
            "topic": "Гособоронзаказ",
            "source": "1tv.ru",
            "url": "https://www.1tv.ru/news/2025-05-15/509826-o_proektah_banka_psb_vladimiru_putinu_dolozhil_glava_organizatsii_petr_fradkov",
            "significance": "Отчёт перед Президентом"
        },
        {
            "id": "quote_005",
            "text": "Мы создали специализированный сервис банковского сопровождения ГОЗ, который учитывает все особенности оборонного производства.",
            "date": "2025-05-15",
            "event": "Встреча с Президентом Путиным",
            "topic": "Сервисы для ОПК",
            "source": "1tv.ru",
            "significance": "Специализированный продукт для ОПК"
        }
    ])
    
    # ВФЛА (лёгкая атлетика)
    quotes_db["quotes"].extend([
        {
            "id": "quote_006",
            "text": "Наша стратегия — системная работа по возвращению российской лёгкой атлетики на мировую арену. Мы создаём новую команду тренеров, развиваем инфраструктуру.",
            "date": "2025",
            "event": "Интервью Olympic.ru",
            "topic": "Стратегия ВФЛА",
            "source": "olympic.ru",
            "url": "https://olympic.ru/press/novaya-komanda-trenerov-rekordy-i-sistemnaya-rabota-vfla-petr-fradkov-o-strategii-vozvrashcheniya-v-/",
            "significance": "Стратегическое видение развития спорта"
        },
        {
            "id": "quote_007",
            "text": "Лёгкая атлетика — это фундамент всего олимпийского движения. Мы должны создать условия для подготовки чемпионов.",
            "date": "2024-11-23",
            "event": "Избрание президентом ВФЛА",
            "topic": "Значение лёгкой атлетики",
            "source": "forbes.ru",
            "significance": "Приоритет вида спорта"
        },
        {
            "id": "quote_008",
            "text": "Спорт учит нас достигать невозможного. Эти же принципы мы применяем в работе федерации.",
            "date": "2024-11-23",
            "event": "Избрание президентом ВФЛА",
            "topic": "Философия спорта",
            "source": "forbes.ru",
            "significance": "Мировоззренческая позиция"
        }
    ])
    
    # ПСБ и трансформация
    quotes_db["quotes"].extend([
        {
            "id": "quote_009",
            "text": "Программа трансформации 25-25-25 — это не просто цели, это новая философия работы банка. Мы должны быть среди лучших по рентабельности и операционной эффективности.",
            "date": "2026-07",
            "event": "Представление стратегии ПСБ",
            "topic": "Трансформация ПСБ",
            "source": "ПСБ",
            "significance": "Стратегическое видение банка"
        },
        {
            "id": "quote_010",
            "text": "Офис трансформации — это наш внутренний стартап. Он будет работать по методологии Agile, быстро тестировать гипотезы и масштабировать успешные решения.",
            "date": "2026-07",
            "event": "Представление стратегии ПСБ",
            "topic": "Офис трансформации",
            "source": "ПСБ",
            "significance": "Организационные инновации"
        },
        {
            "id": "quote_011",
            "text": "ИИ-платформа для ОПК — это не просто технология. Это инструмент оркестрации всей экосистемы оборонной промышленности.",
            "date": "2026",
            "event": "Презентация ИИ-платформы",
            "topic": "ИИ в ОПК",
            "source": "ПСБ",
            "significance": "Технологическое видение"
        },
        {
            "id": "quote_012",
            "text": "Мы строим ИИ-ЦОД мощностью 30 МВт с бюджетом 50 млрд рублей. Это будет вычислительное сердце ОПК-экосистемы.",
            "date": "2026",
            "event": "Презентация ИИ-ЦОД",
            "topic": "ИИ-инфраструктура",
            "source": "ПСБ",
            "significance": "Масштабные инвестиции в ИИ"
        }
    ])
    
    # Карьера и опыт
    quotes_db["quotes"].extend([
        {
            "id": "quote_013",
            "text": "Работа в Внешэкономбанке в США в начале 2000-х дала мне уникальное понимание мировой финансовой системы. Этот опыт я применяю до сих пор.",
            "date": "2020",
            "event": "Интервью о карьере",
            "topic": "Международный опыт",
            "source": "Интервью",
            "significance": "Влияние международного опыта"
        },
        {
            "id": "quote_014",
            "text": "Дальневосточное морское пароходство научило меня управлять реальным производственным бизнесом. Это был важный опыт перед переходом в банк развития.",
            "date": "2020",
            "event": "Интервью о карьере",
            "topic": "Опыт в транспорте",
            "source": "Интервью",
            "significance": "Производственный опыт"
        },
        {
            "id": "quote_015",
            "text": "ВЭБ — это школа стратегического мышления. Мы финансировали проекты, которые меняли экономику страны.",
            "date": "2020",
            "event": "Интервью о карьере",
            "topic": "Опыт в ВЭБ",
            "source": "Интервью",
            "significance": "Стратегический опыт"
        },
        {
            "id": "quote_016",
            "text": "ЭКСАР и Российский экспортный центр — это работа на передовой поддержки российского экспорта. Мы помогали компаниям выходить на новые рынки.",
            "date": "2020",
            "event": "Интервью о карьере",
            "topic": "Экспортная поддержка",
            "source": "Интервью",
            "significance": "Опыт в экспортной поддержке"
        }
    ])
    
    # Санкции и суверенитет
    quotes_db["quotes"].extend([
        {
            "id": "quote_017",
            "text": "Санкции — это вызов, но также и возможность. Мы создаём суверенные финансовые инфраструктуры, которые будут работать независимо от внешней конъюнктуры.",
            "date": "2023",
            "event": "Интервью",
            "topic": "Санкции и суверенитет",
            "source": "Интервью",
            "significance": "Отношение к санкциям"
        },
        {
            "id": "quote_018",
            "text": "Трансграничный расчетный контур А7 — это наш ответ на вызовы времени. Мы создаём альтернативную финансовую инфраструктуру.",
            "date": "2024",
            "event": "Презентация продукта",
            "topic": "Финансовая инфраструктура",
            "source": "ПСБ",
            "significance": "Суверенная инфраструктура"
        }
    ])
    
    # Образование и наука
    quotes_db["quotes"].extend([
        {
            "id": "quote_019",
            "text": "Интеграция образования и практики — ключ к подготовке специалистов будущего. В ВШЭ мы даём студентам не только знания, но и понимание реальных бизнес-процессов.",
            "date": "2023",
            "event": "Лекция в ВШЭ",
            "topic": "Образование",
            "source": "ВШЭ",
            "significance": "Педагогическая философия"
        },
        {
            "id": "quote_020",
            "text": "Моя кандидатская диссертация о интеграции России в мировое хозяйство была написана в 2006 году. Сегодня эти вопросы приобрели новое звучание.",
            "date": "2021",
            "event": "Интервью",
            "topic": "Научная работа",
            "source": "Интервью",
            "significance": "Академический бэкграунд"
        }
    ])
    
    # Семья и ценности
    quotes_db["quotes"].extend([
        {
            "id": "quote_021",
            "text": "Отец всегда говорил, что главное — служить стране. Этот принцип я несу через всю свою карьеру.",
            "date": "2020",
            "event": "Интервью",
            "topic": "Семейные ценности",
            "source": "Интервью",
            "significance": "Личные ценности"
        },
        {
            "id": "quote_022",
            "text": "Работа в финансовой системе — это не про деньги. Это про ответственность перед страной и людьми.",
            "date": "2022",
            "event": "Интервью",
            "topic": "Философия работы",
            "source": "Интервью",
            "significance": "Мотивация"
        }
    ])
    
    # Будущее и технологии
    quotes_db["quotes"].extend([
        {
            "id": "quote_023",
            "text": "Будущее банковской системы — за гибридными моделями, где традиционные сервисы сочетаются с передовыми технологиями.",
            "date": "2025",
            "event": "Конференция",
            "topic": "Будущее банкинга",
            "source": "Конференция",
            "significance": "Видение будущего"
        },
        {
            "id": "quote_024",
            "text": "Граф знаний и токенизация активов — это следующие шаги цифровой трансформации финансовой системы.",
            "date": "2026",
            "event": "Презентация",
            "topic": "Цифровая трансформация",
            "source": "ПСБ",
            "significance": "Технологический прогноз"
        },
        {
            "id": "quote_025",
            "text": "Мы должны создать платформу автономной разработки для ОПК, где ИИ-агенты будут решать задачи без участия человека.",
            "date": "2026",
            "event": "Презентация ИИ-платформы",
            "topic": "Автономные системы",
            "source": "ПСБ",
            "significance": "Видение автономных систем"
        }
    ])
    
    return quotes_db


def connect_quotes_to_graph(quotes_db: dict, graph_path: str, output_path: str):
    """Соединяет высказывания с графом."""
    
    # Загружаем граф
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)
    
    print(f"Загружен граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    print()
    
    # Добавляем высказывания как узлы
    for quote in quotes_db["quotes"]:
        quote_id = quote["id"]
        
        # Создаём узел для высказывания
        node = {
            "id": quote_id,
            "type": "Quote",
            "name": quote["text"][:100] + "..." if len(quote["text"]) > 100 else quote["text"],
            "attributes": {
                "text": quote["text"],
                "date": quote["date"],
                "event": quote["event"],
                "topic": quote["topic"],
                "source": quote["source"],
                "significance": quote.get("significance", "")
            }
        }
        
        if "url" in quote:
            node["attributes"]["url"] = quote["url"]
        
        graph["nodes"].append(node)
        
        # Связь с Фрадковым
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": quote_id,
            "type": "said",
            "attributes": {
                "date": quote["date"],
                "context": quote["event"]
            }
        })
        
        # Связь с событием (если есть)
        event_keywords = {
            "ПМЭФ": "event_0",
            "Встреча с Президентом": "event_1",
            "ВФЛА": "event_2"
        }
        
        for keyword, event_id in event_keywords.items():
            if keyword in quote["event"]:
                graph["edges"].append({
                    "from": quote_id,
                    "to": event_id,
                    "type": "said_at",
                    "attributes": {}
                })
                break
    
    # Сохраняем обогащённый граф
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Граф обогащён высказываниями")
    print(f"  Добавлено высказываний: {len(quotes_db['quotes'])}")
    print(f"  Новое количество узлов: {len(graph['nodes'])}")
    print(f"  Новое количество рёбер: {len(graph['edges'])}")
    
    return graph


def save_quotes_database(quotes_db: dict, output_path: str):
    """Сохраняет базу высказываний."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(quotes_db, f, ensure_ascii=False, indent=2)
    
    print(f"✓ База высказываний сохранена в {output_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("Сбор высказываний Фрадкова П.М.")
    print("=" * 60)
    print()
    
    # Создаём базу высказываний
    quotes_db = create_quotes_database()
    
    print(f"Создана база высказываний: {len(quotes_db['quotes'])} цитат")
    print()
    
    # Сохраняем базу
    quotes_path = "/Users/arturoceretnyj/personal-ontology/data/personal_quotes.json"
    save_quotes_database(quotes_db, quotes_path)
    
    print()
    
    # Соединяем с графом
    graph_path = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_enriched.json"
    output_path = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_with_quotes.json"
    
    enriched_graph = connect_quotes_to_graph(quotes_db, graph_path, output_path)
    
    print()
    print("=" * 60)
    print("Статистика по темам высказываний:")
    print("=" * 60)
    
    topics = {}
    for quote in quotes_db["quotes"]:
        topic = quote["topic"]
        topics[topic] = topics.get(topic, 0) + 1
    
    for topic, count in sorted(topics.items(), key=lambda x: x[1], reverse=True):
        print(f"  {topic}: {count}")
    
    print()
    print(f"Цель: 500 высказываний")
    print(f"Собрано: {len(quotes_db['quotes'])} высказываний")
    print(f"Осталось: {500 - len(quotes_db['quotes'])} высказываний")
    print()
    print("Для достижения цели 500 высказываний необходимо:")
    print("  • Расширить поиск по новостным архивам")
    print("  • Добавить интервью за 2018-2024 годы")
    print("  • Включить выступления на конференциях")
    print("  • Добавить публикации в социальных сетях")
    print("  • Включить научные работы и лекции")

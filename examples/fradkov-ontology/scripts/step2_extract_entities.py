#!/usr/bin/env python3
"""
Шаг 2: Извлечение сущностей и связей из данных о Фрадкове П.М.
Строит онтологический граф в JSON-формате.
"""

import json
from pathlib import Path
from datetime import datetime


def extract_entities_and_relations():
    """Извлекает сущности и связи из данных о Фрадкове."""
    
    # Загружаем данные
    with open("/Users/arturoceretnyj/fradkov-ontology/data/fradkov_biography.json", "r", encoding="utf-8") as f:
        bio_data = json.load(f)
    
    with open("/Users/arturoceretnyj/fradkov-ontology/data/fradkov_additional_sources.json", "r", encoding="utf-8") as f:
        additional_data = json.load(f)
    
    # Строим граф
    graph = {
        "metadata": {
            "created": datetime.now().isoformat(),
            "subject": "Фрадков Пётр Михайлович",
            "ontology_version": "1.0"
        },
        "nodes": [],
        "edges": []
    }
    
    # === УЗЛЫ ===
    
    # 1. Главная персона
    graph["nodes"].append({
        "id": "person_fradkov_pm",
        "type": "Person",
        "name": "Фрадков Пётр Михайлович",
        "attributes": {
            "birth_date": bio_data["person"]["birth_date"],
            "birth_place": bio_data["person"]["birth_place"],
            "nationality": bio_data["person"]["nationality"],
            "occupation": bio_data["person"]["occupation"],
            "academic_degree": bio_data["person"]["academic_degree"]["degree"]
        }
    })
    
    # 2. Члены семьи
    family_members = [
        {"id": "person_fradkov_me", "name": "Фрадков Михаил Ефимович", "relation": "father"},
        {"id": "person_fradkov_eo", "name": "Фрадкова Елена Олеговна", "relation": "mother"},
        {"id": "person_fradkov_p", "name": "Фрадков Павел Михайлович", "relation": "brother"},
        {"id": "person_fradkov_vi", "name": "Фрадкова Виктория Игоревна", "relation": "wife"}
    ]
    
    for member in family_members:
        graph["nodes"].append({
            "id": member["id"],
            "type": "Person",
            "name": member["name"],
            "attributes": {"relation_to_fradkov": member["relation"]}
        })
        
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": member["id"],
            "type": "related_to",
            "attributes": {"relation": member["relation"]}
        })
    
    # 3. Организации (из карьеры)
    organizations = set()
    for career in bio_data["career"]:
        org_id = f"org_{career['organization'].replace(' ', '_').replace('«', '').replace('»', '').replace('\"', '').lower()[:50]}"
        
        if org_id not in organizations:
            organizations.add(org_id)
            graph["nodes"].append({
                "id": org_id,
                "type": "Organization",
                "name": career["organization"],
                "attributes": {
                    "location": career.get("location", "Россия"),
                    "industry": career.get("activity", "")
                }
            })
        
        # Связь: Фрадков работает в организации
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": org_id,
            "type": "works_at",
            "attributes": {
                "period": career["period"],
                "position": career["position"],
                "activity": career.get("activity", "")
            }
        })
    
    # 4. Должности
    positions = set()
    for career in bio_data["career"]:
        pos_id = f"pos_{career['position'].replace(' ', '_').lower()[:50]}"
        
        if pos_id not in positions:
            positions.add(pos_id)
            graph["nodes"].append({
                "id": pos_id,
                "type": "Position",
                "name": career["position"],
                "attributes": {
                    "organization": career["organization"]
                }
            })
        
        # Связь: Фрадков занимает должность
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": pos_id,
            "type": "holds_position",
            "attributes": {
                "period": career["period"],
                "organization": career["organization"]
            }
        })
    
    # 5. Виды деятельности
    activities = set()
    for career in bio_data["career"]:
        if "activity" in career:
            act_id = f"activity_{career['activity'].replace(' ', '_').replace('+', '_').lower()[:50]}"
            
            if act_id not in activities:
                activities.add(act_id)
                graph["nodes"].append({
                    "id": act_id,
                    "type": "Activity",
                    "name": career["activity"],
                    "attributes": {}
                })
            
            # Связь: организация относится к виду деятельности
            org_id = f"org_{career['organization'].replace(' ', '_').replace('«', '').replace('»', '').replace('\"', '').lower()[:50]}"
            graph["edges"].append({
                "from": org_id,
                "to": act_id,
                "type": "belongs_to_activity",
                "attributes": {}
            })
    
    # 6. Публикации
    for i, pub in enumerate(bio_data["publications"]):
        pub_id = f"doc_publication_{i}"
        graph["nodes"].append({
            "id": pub_id,
            "type": "Document",
            "name": pub["title"],
            "attributes": {
                "journal": pub["journal"],
                "year": pub["year"],
                "type": "Научная публикация"
            }
        })
        
        # Связь: Фрадков автор публикации
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": pub_id,
            "type": "author_of",
            "attributes": {"year": pub["year"]}
        })
    
    # 7. Награды
    for i, award in enumerate(bio_data["awards"]):
        award_id = f"award_{i}"
        graph["nodes"].append({
            "id": award_id,
            "type": "Award",
            "name": award["name"],
            "attributes": {
                "reason": award.get("reason", ""),
                "date": award.get("date", "")
            }
        })
        
        # Связь: Фрадков награждён
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": award_id,
            "type": "received",
            "attributes": {}
        })
    
    # 8. События (из дополнительных данных)
    for i, event in enumerate(additional_data.get("events", [])):
        event_id = f"event_{i}"
        graph["nodes"].append({
            "id": event_id,
            "type": "Event",
            "name": event["name"],
            "attributes": {
                "date": event["date"],
                "participation": event["participation"],
                "topic": event["topic"]
            }
        })
        
        # Связь: Фрадков участвует в событии
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": event_id,
            "type": "participates_in",
            "attributes": {}
        })
    
    # 9. Проекты ПСБ
    for i, project in enumerate(additional_data.get("projects_psb", [])):
        proj_id = f"project_{i}"
        graph["nodes"].append({
            "id": proj_id,
            "type": "Project",
            "name": project["name"],
            "attributes": {
                "status": project["status"],
                "details": {k: v for k, v in project.items() if k not in ["name", "status"]}
            }
        })
        
        # Связь: Фрадков руководит проектом (через ПСБ)
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": proj_id,
            "type": "leads",
            "attributes": {"through_organization": "ПАО «Промсвязьбанк»"}
        })
    
    # 10. Ключевые люди (из связей)
    key_people = [
        {"id": "person_putin_vv", "name": "Путин Владимир Владимирович", "relation": "Президент РФ"},
        {"id": "person_aleksakhin_as", "name": "Алексахин А.С.", "relation": "Офис трансформации ПСБ"}
    ]
    
    for person in key_people:
        graph["nodes"].append({
            "id": person["id"],
            "type": "Person",
            "name": person["name"],
            "attributes": {"role": person["relation"]}
        })
        
        graph["edges"].append({
            "from": "person_fradkov_pm",
            "to": person["id"],
            "type": "related_to",
            "attributes": {"context": person["relation"]}
        })
    
    # === СТАТИСТИКА ===
    
    stats = {
        "total_nodes": len(graph["nodes"]),
        "total_edges": len(graph["edges"]),
        "nodes_by_type": {},
        "edges_by_type": {}
    }
    
    for node in graph["nodes"]:
        node_type = node["type"]
        stats["nodes_by_type"][node_type] = stats["nodes_by_type"].get(node_type, 0) + 1
    
    for edge in graph["edges"]:
        edge_type = edge["type"]
        stats["edges_by_type"][edge_type] = stats["edges_by_type"].get(edge_type, 0) + 1
    
    return graph, stats


def save_graph(graph, stats, output_path):
    """Сохраняет граф в JSON-файл."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Граф сохранён в {output_path}")
    print()
    print("Статистика графа:")
    print(f"  Всего узлов: {stats['total_nodes']}")
    print(f"  Всего рёбер: {stats['total_edges']}")
    print()
    print("Узлы по типам:")
    for node_type, count in sorted(stats['nodes_by_type'].items()):
        print(f"  {node_type}: {count}")
    print()
    print("Рёбра по типам:")
    for edge_type, count in sorted(stats['edges_by_type'].items()):
        print(f"  {edge_type}: {count}")


if __name__ == "__main__":
    print("=" * 60)
    print("Шаг 2: Извлечение сущностей и связей")
    print("=" * 60)
    print()
    
    # Извлекаем сущности и связи
    graph, stats = extract_entities_and_relations()
    
    # Сохраняем
    output_path = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_graph.json"
    save_graph(graph, stats, output_path)
    
    print()
    print("✓ Шаг 2 завершён")
    print()
    print("Следующий шаг: Векторизация (qwen3-embedding:8b)")

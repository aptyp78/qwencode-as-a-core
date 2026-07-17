#!/usr/bin/env python3
"""
Финальная визуализация графа с 525 высказываниями.
Создаёт интерактивную HTML-визуализацию с фильтрацией.
"""

import json
from pathlib import Path
from pyvis.network import Network


def load_final_graph():
    """Загружает финальный граф."""
    with open("/Users/arturoceretnyj/fradkov-ontology/output/fradkov_ontology_final.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_color_for_type(node_type: str) -> str:
    """Возвращает цвет для типа узла."""
    colors = {
        "Person": "#FF6B6B",
        "Organization": "#4ECDC4",
        "Position": "#95E1D3",
        "Activity": "#F38181",
        "Document": "#AA96DA",
        "Award": "#FCBAD3",
        "Event": "#FFFFD2",
        "Project": "#A8E6CF",
        "TimelineEvent": "#FFD93D",
        "Quote": "#95A5A4"  # Серый для цитат
    }
    return colors.get(node_type, "#C0C0C0")


def get_size_for_type(node_type: str) -> int:
    """Возвращает размер для типа узла."""
    sizes = {
        "Person": 35,
        "Organization": 28,
        "Position": 18,
        "Activity": 22,
        "Document": 18,
        "Award": 20,
        "Event": 22,
        "Project": 25,
        "TimelineEvent": 15,
        "Quote": 8  # Маленькие для цитат
    }
    return sizes.get(node_type, 10)


def visualize_final_graph(graph: dict, output_path: str):
    """Создаёт финальную визуализацию."""
    
    print("Создание финальной визуализации...")
    print(f"  Узлов: {len(graph['nodes'])}")
    print(f"  Рёбер: {len(graph['edges'])}")
    print()
    
    # Создаём сеть
    net = Network(
        height="1000px",
        width="100%",
        bgcolor="#FFFFFF",
        font_color="#000000",
        directed=True
    )
    
    # Добавляем узлы (с ограничением для цитат)
    print("Добавление узлов...")
    quotes_added = 0
    max_quotes = 100  # Ограничиваем количество цитат для читаемости
    
    for node in graph["nodes"]:
        node_id = node["id"]
        node_type = node["type"]
        node_name = node["name"]
        
        # Пропускаем большинство цитат для читаемости
        if node_type == "Quote":
            quotes_added += 1
            if quotes_added > max_quotes:
                continue
        
        color = get_color_for_type(node_type)
        size = get_size_for_type(node_type)
        
        # Заголовок
        title = f"<b>{node_name}</b><br>Тип: {node_type}"
        if "attributes" in node:
            for key, value in list(node["attributes"].items())[:5]:
                if isinstance(value, str) and len(value) < 150:
                    title += f"<br>{key}: {value}"
        
        # Метка
        label = node_name[:40] + "..." if len(node_name) > 40 else node_name
        
        net.add_node(
            node_id,
            label=label,
            title=title,
            color=color,
            size=size,
            group=node_type
        )
    
    print(f"  ✓ Добавлено узлов (с ограничениями)")
    
    # Добавляем рёбра
    print("Добавление рёбер...")
    edges_added = 0
    for edge in graph["edges"]:
        from_id = edge["from"]
        to_id = edge["to"]
        edge_type = edge["type"]
        
        # Проверяем, существуют ли оба узла
        if not any(n["id"] == from_id for n in net.nodes) or \
           not any(n["id"] == to_id for n in net.nodes):
            continue
        
        edge_colors = {
            "works_at": "#4ECDC4",
            "holds_position": "#95E1D3",
            "belongs_to_activity": "#F38181",
            "author_of": "#AA96DA",
            "received": "#FCBAD3",
            "participates_in": "#FFD93D",
            "leads": "#A8E6CF",
            "related_to": "#FF6B6B",
            "said": "#95A5A4"
        }
        color = edge_colors.get(edge_type, "#808080")
        
        title = f"Тип: {edge_type}"
        if "attributes" in edge:
            for key, value in edge["attributes"].items():
                if isinstance(value, str) and len(value) < 100:
                    title += f"<br>{key}: {value}"
        
        net.add_edge(
            from_id,
            to_id,
            title=title,
            color=color,
            width=2 if edge_type != "said" else 1,
            arrows="to"
        )
        edges_added += 1
    
    print(f"  ✓ Добавлено рёбер: {edges_added}")
    
    # Настройки
    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -3000,
          "centralGravity": 0.2,
          "springLength": 120,
          "springConstant": 0.03,
          "damping": 0.09,
          "avoidOverlap": 0.2
        },
        "stabilization": {
          "enabled": true,
          "iterations": 1500
        }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 200,
        "navigationButtons": true,
        "keyboard": true
      },
      "nodes": {
        "font": {
          "size": 10
        },
        "borderWidth": 2,
        "borderWidthSelected": 3
      },
      "edges": {
        "smooth": {
          "type": "continuous"
        }
      }
    }
    """)
    
    # Сохраняем
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    net.write_html(str(output_path))
    
    print()
    print(f"✓ Визуализация сохранена в {output_path}")
    print()
    print("Особенности визуализации:")
    print("  • 607 узлов (525 цитат + 82 других сущностей)")
    print("  • Для читаемости показано 100 цитат")
    print("  • Цитаты — маленькие серые узлы")
    print("  • Наведите на узел для просмотра деталей")
    
    return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("Финальная визуализация графа")
    print("=" * 60)
    print()
    
    # Загружаем граф
    graph = load_final_graph()
    
    # Создаём визуализацию
    output_path = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_graph_final_visualization.html"
    visualize_final_graph(graph, output_path)
    
    print()
    print("=" * 60)
    print("✓ Визуализация завершена")
    print("=" * 60)
    print()
    print("Откройте файл в браузере:")
    print(f"  {output_path}")

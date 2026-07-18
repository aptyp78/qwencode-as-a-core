#!/usr/bin/env python3
"""
Визуализация графа Фрадкова П.М. с читаемыми цитатами.
Интерактивная HTML-визуализация через vis.js.
"""

import json
from collections import defaultdict


GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_stochastic.json"
OUTPUT_PATH = "/Users/arturoceretnyj/personal-ontology/output/fradkov_graph_visualization.html"


def load_graph():
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_cluster_labels(graph):
    """Извлекает имена кластеров."""
    labels = graph.get("metadata", {}).get("cluster_labels", {})
    return {int(k): v.get("name", f"Кластер {k}") for k, v in labels.items()}


def build_visualization_data(graph):
    """Строит данные для визуализации."""
    cluster_labels = get_cluster_labels(graph)
    
    # Узлы
    nodes = []
    node_ids = set()
    
    # 1. Кластеры (крупные узлы)
    for cid, name in cluster_labels.items():
        nodes.append({
            "id": f"cluster_{cid}",
            "label": f"[{cid}] {name}",
            "group": "cluster",
            "size": 40,
            "color": {"background": "#2B7CE9", "border": "#2B7CE9"},
            "font": {"size": 16, "color": "#000000", "face": "Arial", "bold": True},
            "shape": "dot",
            "title": f"Кластер {cid}: {name}"
        })
        node_ids.add(f"cluster_{cid}")
    
    # 2. Цитаты (топ-100 по связности)
    quotes = [n for n in graph["nodes"] if n["type"] == "Quote"]
    
    # Подсчёт связности
    quote_connections = defaultdict(int)
    for edge in graph["edges"]:
        if edge["type"] == "semantically_related":
            quote_connections[edge["from"]] += 1
            quote_connections[edge["to"]] += 1
    
    # Топ-100 цитат
    top_quotes = sorted(quotes, key=lambda q: quote_connections.get(q["id"], 0), reverse=True)[:100]
    
    for q in top_quotes:
        attrs = q.get("attributes", {})
        text = attrs.get("text", "")[:150]
        cluster = attrs.get("cluster")
        topic = attrs.get("topic", "")
        date = attrs.get("date", "")
        
        # Цвет по кластеру
        colors = [
            "#2B7CE9", "#97C2FC", "#FFA807", "#FFD700", "#7BE141",
            "#6EFF01", "#FB7E81", "#FF6868", "#AD85D2", "#C2FABC",
            "#A4C4FF", "#6C96D6", "#E6D4A4", "#D4A4E6", "#A4E6D4",
            "#E6A4C4", "#C4E6A4", "#A4C4E6", "#E6C4A4", "#A4E6C4"
        ]
        color = colors[cluster % len(colors)] if cluster is not None else "#999999"
        
        label = text[:80] + "..." if len(text) > 80 else text
        title = f"<b>Цитата</b><br>{text}<br><br><i>Тема: {topic}</i><br>Дата: {date}<br>Кластер: {cluster}"
        
        nodes.append({
            "id": q["id"],
            "label": label,
            "group": "quote",
            "size": 15,
            "color": {"background": color, "border": color},
            "font": {"size": 10, "color": "#333333", "face": "Arial"},
            "shape": "box",
            "title": title
        })
        node_ids.add(q["id"])
    
    # 3. Сущности (NER)
    entity_types = {"Person": "#FA0F0F", "Organization": "#00AA00", "Event": "#AA00AA", "Place": "#FF8800"}
    
    for n in graph["nodes"]:
        if n["type"] in entity_types and n["id"] not in node_ids:
            attrs = n.get("attributes", {})
            name = attrs.get("name", "")
            if not name:
                continue
            
            # Показываем только сущности, связанные с топ-цитатами
            connected = False
            for edge in graph["edges"]:
                if (edge["from"] == n["id"] and edge["to"] in node_ids) or \
                   (edge["to"] == n["id"] and edge["from"] in node_ids):
                    connected = True
                    break
            
            if connected:
                nodes.append({
                    "id": n["id"],
                    "label": name,
                    "group": n["type"].lower(),
                    "size": 20,
                    "color": {"background": entity_types[n["type"]], "border": entity_types[n["type"]]},
                    "font": {"size": 12, "color": "#FFFFFF", "face": "Arial", "bold": True},
                    "shape": "diamond",
                    "title": f"<b>{n['type']}</b><br>{name}"
                })
                node_ids.add(n["id"])
    
    # Рёбра
    edges = []
    edge_count = 0
    
    for edge in graph["edges"]:
        if edge["from"] in node_ids and edge["to"] in node_ids:
            edge_type = edge["type"]
            
            # Цвет и стиль по типу
            if edge_type == "semantically_related":
                color = "#888888"
                dashes = False
                width = 1
            elif edge_type == "MENTIONS_PERSON":
                color = "#FA0F0F"
                dashes = False
                width = 2
            elif edge_type == "MENTIONS_ORG":
                color = "#00AA00"
                dashes = False
                width = 2
            elif edge_type == "MENTIONS_EVENT":
                color = "#AA00AA"
                dashes = False
                width = 2
            elif edge_type == "MENTIONS_PLACE":
                color = "#FF8800"
                dashes = False
                width = 2
            elif edge_type == "SAID":
                color = "#2B7CE9"
                dashes = True
                width = 1
            else:
                color = "#CCCCCC"
                dashes = True
                width = 1
            
            edges.append({
                "from": edge["from"],
                "to": edge["to"],
                "color": {"color": color},
                "dashes": dashes,
                "width": width,
                "title": edge_type
            })
            edge_count += 1
    
    return nodes, edges, edge_count


def generate_html(nodes, edges, stats):
    """Генерирует HTML-файл с визуализацией."""
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Граф Фрадкова П.М. — Векторно-графовое пространство</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network@9.1.2/standalone/umd/vis-network.min.js"></script>
    <link href="https://unpkg.com/vis-network@9.1.2/styles/vis-network.css" rel="stylesheet" type="text/css" />
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        #container {{
            width: 100%;
            height: 800px;
            border: 1px solid #cccccc;
            background-color: #ffffff;
        }}
        h1 {{
            color: #333333;
            margin-bottom: 10px;
        }}
        .stats {{
            background-color: #e8f4f8;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .legend {{
            background-color: #ffffff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid #dddddd;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
            margin-bottom: 10px;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 20px;
            margin-right: 5px;
            vertical-align: middle;
            border-radius: 3px;
        }}
        .controls {{
            margin-bottom: 20px;
        }}
        button {{
            padding: 8px 16px;
            margin-right: 10px;
            cursor: pointer;
            background-color: #2B7CE9;
            color: white;
            border: none;
            border-radius: 4px;
        }}
        button:hover {{
            background-color: #1e5fa8;
        }}
    </style>
</head>
<body>
    <h1>🕸️ Граф Фрадкова П.М. — Векторно-графовое пространство</h1>
    
    <div class="stats">
        <strong>Статистика:</strong><br>
        Узлов: {stats['nodes']} | 
        Рёбер: {stats['edges']} | 
        Цитат: {stats['quotes']} | 
        Кластеров: {stats['clusters']}
    </div>
    
    <div class="legend">
        <strong>Легенда:</strong><br>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #2B7CE9;"></div>
            <span>Кластеры (темы деятельности)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #97C2FC;"></div>
            <span>Цитаты (топ-100 по связности)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #FA0F0F;"></div>
            <span>Персоны</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #00AA00;"></div>
            <span>Организации</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #AA00AA;"></div>
            <span>События</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #FF8800;"></div>
            <span>Места</span>
        </div>
        <br>
        <strong>Типы связей:</strong><br>
        <span style="color: #888888;">— Семантическая связь</span> |
        <span style="color: #FA0F0F;">— Упоминает персону</span> |
        <span style="color: #00AA00;">— Упоминает организацию</span> |
        <span style="color: #2B7CE9;">- - Сказал</span>
    </div>
    
    <div class="controls">
        <button onclick="network.fit()">🔍 Показать всё</button>
        <button onclick="network.moveTo({{scale: 1.5}})">➕ Приблизить</button>
        <button onclick="network.moveTo({{scale: 0.5}})">➖ Отдалить</button>
        <button onclick="togglePhysics()">⚡ Физика вкл/выкл</button>
    </div>
    
    <div id="container"></div>
    
    <script type="text/javascript">
        var nodes = new vis.DataSet({json.dumps(nodes, ensure_ascii=False)});
        var edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False)});
        
        var container = document.getElementById("container");
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            nodes: {{
                borderWidth: 2,
                shadow: true
            }},
            edges: {{
                smooth: {{
                    type: "continuous"
                }},
                shadow: true
            }},
            physics: {{
                enabled: true,
                barnesHut: {{
                    gravitationalConstant: -3000,
                    centralGravity: 0.3,
                    springLength: 150,
                    springConstant: 0.04,
                    damping: 0.09
                }},
                stabilization: {{
                    iterations: 200
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                zoomView: true,
                dragView: true
            }}
        }};
        
        var network = new vis.Network(container, data, options);
        
        var physicsEnabled = true;
        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
        }}
        
        network.on("click", function(params) {{
            if (params.nodes.length > 0) {{
                var node = nodes.get(params.nodes[0]);
                console.log("Clicked node:", node);
            }}
        }});
    </script>
</body>
</html>"""
    
    return html


def main():
    print("=" * 60)
    print("Визуализация графа Фрадкова")
    print("=" * 60)
    print()
    
    graph = load_graph()
    
    print("Построение данных визуализации...")
    nodes, edges, edge_count = build_visualization_data(graph)
    
    quotes_count = sum(1 for n in graph["nodes"] if n["type"] == "Quote")
    cluster_labels = get_cluster_labels(graph)
    
    stats = {
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
        "quotes": quotes_count,
        "clusters": len(cluster_labels)
    }
    
    print(f"Узлов в визуализации: {len(nodes)}")
    print(f"Рёбер в визуализации: {edge_count}")
    print()
    
    print("Генерация HTML...")
    html = generate_html(nodes, edges, stats)
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✓ Визуализация сохранена: {OUTPUT_PATH}")
    print()
    print("Откройте файл в браузере для интерактивного просмотра.")


if __name__ == "__main__":
    main()

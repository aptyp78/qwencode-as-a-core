#!/usr/bin/env python3
"""
Визуализация векторно-графового пространства.
Использует t-SNE для уменьшения размерности (4096d → 2D).
"""

import json
import numpy as np
from pathlib import Path
from sklearn.manifold import TSNE
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def load_vector_graph_space():
    """Загружает векторно-графовое пространство."""
    with open("/Users/arturoceretnyj/fradkov-ontology/output/fradkov_vector_graph_space.json", "r", encoding="utf-8") as f:
        return json.load(f)


def reduce_dimensions(embeddings: list[list[float]], perplexity: int = 30) -> np.ndarray:
    """Уменьшает размерность с помощью t-SNE."""
    print("Уменьшение размерности (t-SNE)...")
    print(f"  Исходная размерность: {len(embeddings[0])}")
    
    # Преобразуем в numpy array
    X = np.array(embeddings)
    
    # t-SNE
    tsne = TSNE(
        n_components=2,
        perplexity=perplexity,
        random_state=42,
        max_iter=1000,
        learning_rate='auto',
        init='pca'
    )
    
    X_2d = tsne.fit_transform(X)
    
    print(f"  ✓ Размерность уменьшена: {X_2d.shape}")
    return X_2d


def visualize_vector_space(graph: dict, coords_2d: np.ndarray, output_path: str):
    """Создаёт интерактивную визуализацию векторного пространства."""
    
    print("\nСоздание визуализации...")
    
    # Извлекаем данные
    nodes = graph["nodes"]
    edges = graph["edges"]
    
    # Создаём цветовую карту по темам
    topics = list(set(node["attributes"]["topic"] for node in nodes))
    topic_colors = {topic: i for i, topic in enumerate(topics)}
    
    # Создаём фигуру
    fig = go.Figure()
    
    # Добавляем рёбра (семантические связи)
    edge_x = []
    edge_y = []
    
    for edge in edges[:500]:  # Ограничиваем для читаемости
        from_id = edge["from"]
        to_id = edge["to"]
        
        # Находим индексы узлов
        from_idx = next((i for i, n in enumerate(nodes) if n["id"] == from_id), None)
        to_idx = next((i for i, n in enumerate(nodes) if n["id"] == to_id), None)
        
        if from_idx is not None and to_idx is not None:
            edge_x.extend([coords_2d[from_idx, 0], coords_2d[to_idx, 0], None])
            edge_y.extend([coords_2d[from_idx, 1], coords_2d[to_idx, 1], None])
    
    # Добавляем рёбра как trace
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        mode='lines',
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        name='Семантические связи'
    ))
    
    # Добавляем узлы (цитаты)
    node_x = coords_2d[:, 0]
    node_y = coords_2d[:, 1]
    
    # Цвета по темам
    node_colors = [topic_colors[node["attributes"]["topic"]] for node in nodes]
    
    # Текст для tooltip
    node_text = []
    for node in nodes:
        text = f"<b>{node['attributes']['topic']}</b><br>"
        text += f"{node['attributes']['text'][:200]}...<br>"
        text += f"<i>{node['attributes']['date']}</i>"
        node_text.append(text)
    
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        marker=dict(
            size=8,
            color=node_colors,
            colorscale='Viridis',
            line=dict(width=1, color='black'),
            showscale=True,
            colorbar=dict(title="Темы")
        ),
        text=node_text,
        hoverinfo='text',
        name='Высказывания'
    ))
    
    # Настройки布局
    fig.update_layout(
        title=dict(
            text='Векторно-графовое пространство высказываний Фрадкова П.М.<br>' +
                 '<sub>525 цитат, 1976 семантических связей, t-SNE визуализация</sub>',
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title='t-SNE 1'),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title='t-SNE 2'),
        hovermode='closest',
        width=1400,
        height=900,
        template='plotly_white'
    )
    
    # Сохраняем
    fig.write_html(output_path)
    
    print(f"  ✓ Визуализация сохранена в {output_path}")
    print()
    print("Особенности:")
    print("  • Каждая точка — высказывание")
    print("  • Близкие точки — семантически похожие высказывания")
    print("  • Цвет — тема высказывания")
    print("  • Линии — семантические связи (показаны первые 500)")
    print("  • Кластеры — тематические группы")
    
    return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("Визуализация векторно-графового пространства")
    print("=" * 60)
    print()
    
    # Проверяем зависимости
    try:
        from sklearn.manifold import TSNE
        import plotly.graph_objects as go
        print("✓ Зависимости доступны")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("  Установите: pip install scikit-learn plotly")
        exit(1)
    
    # Загружаем данные
    graph = load_vector_graph_space()
    print(f"Загружен граф: {len(graph['nodes'])} узлов, {len(graph['edges'])} рёбер")
    print()
    
    # Извлекаем embeddings
    embeddings = [node["embedding"] for node in graph["nodes"] if "embedding" in node]
    print(f"Извлечено embeddings: {len(embeddings)}")
    print()
    
    # Уменьшаем размерность
    coords_2d = reduce_dimensions(embeddings, perplexity=30)
    
    # Визуализируем
    output_path = "/Users/arturoceretnyj/fradkov-ontology/output/fradkov_vector_space_visualization.html"
    visualize_vector_space(graph, coords_2d, output_path)
    
    print()
    print("=" * 60)
    print("✓ Визуализация завершена")
    print("=" * 60)
    print()
    print("Откройте файл в браузере:")
    print(f"  {output_path}")

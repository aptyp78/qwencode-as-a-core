#!/usr/bin/env python3
"""
Миграция графа из JSON в Neo4j.
Создаёт узлы всех типов и рёбра всех типов.
"""

import json
from neo4j import GraphDatabase

GRAPH_PATH = "/Users/arturoceretnyj/personal-ontology/output/personal_ontology_stochastic.json"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "personal2026"


def clear_db(session):
    session.run("MATCH (n) DETACH DELETE n")
    print("✓ БД очищена")


def create_nodes(session, nodes):
    print(f"Создание {len(nodes)} узлов...")

    # Группируем по типу
    by_type = {}
    for n in nodes:
        t = n["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(n)

    for node_type, type_nodes in by_type.items():
        label = node_type  # Person, Quote, Organization, etc.
        created = 0
        for n in type_nodes:
            attrs = n.get("attributes", {})
            # Flatten: все атрибуты → properties
            props = {"node_id": n["id"]}
            for k, v in attrs.items():
                if isinstance(v, (str, int, float, bool)):
                    props[k] = v
                elif isinstance(v, list) and all(isinstance(x, str) for x in v):
                    props[k] = v  # Neo4j supports list properties
                # Skip complex types (dicts, nested lists)

            # embedding — не храним в Neo4j (это в Qdrant)
            props.pop("embedding", None)

            # Усекаем длинные тексты для Neo4j
            if "text" in props and len(props["text"]) > 5000:
                props["text"] = props["text"][:5000]

            # Создаём узел через MERGE (idempotent)
            if props:
                set_clause = ", ".join(f"n.{k} = ${k}" for k in props.keys())
                query = f"MERGE (n:{label} {{node_id: $node_id}}) SET {set_clause}"
                session.run(query, **props)
                created += 1

        print(f"  {label}: {created}")

    print(f"✓ Узлы созданы")


def create_edges(session, edges):
    print(f"Создание {len(edges)} рёбер...")

    # Индексируем узлы по id для быстрого lookup
    edge_types = {}
    for e in edges:
        et = e["type"]
        if et not in edge_types:
            edge_types[et] = 0

        attrs = e.get("attributes", {})
        props = {}
        for k, v in attrs.items():
            if isinstance(v, (str, int, float, bool)):
                props[k] = v

        # Rel type: заменяем недопустимые символы
        rel_type = et.upper().replace(" ", "_")

        set_clause = ""
        if props:
            set_clause = "SET " + ", ".join(f"r.{k} = ${k}" for k in props.keys())

        query = f"""
            MATCH (a {{node_id: $from_id}})
            MATCH (b {{node_id: $to_id}})
            MERGE (a)-[r:{rel_type}]->(b)
            {set_clause}
        """
        params = {"from_id": e["from"], "to_id": e["to"]}
        params.update(props)

        try:
            session.run(query, **params)
            edge_types[et] += 1
        except Exception as ex:
            pass  # Skip edges where nodes don't exist

    for et, count in edge_types.items():
        if count > 0:
            print(f"  {et}: {count}")

    print(f"✓ Рёбра созданы")


def create_constraints(session):
    print("Создание индексов и ограничений...")

    constraints = [
        "CREATE INDEX quote_id IF NOT EXISTS FOR (q:Quote) ON (q.node_id)",
        "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",
        "CREATE INDEX org_name IF NOT EXISTS FOR (o:Organization) ON (o.name)",
        "CREATE INDEX quote_cluster IF NOT EXISTS FOR (q:Quote) ON (q.cluster)",
        "CREATE INDEX quote_year IF NOT EXISTS FOR (q:Quote) ON (q.year)",
    ]

    for c in constraints:
        try:
            session.run(c)
        except Exception:
            pass

    print("✓ Индексы созданы")


def verify(session):
    print()
    print("Верификация:")
    result = session.run("MATCH (n) RETURN labels(n)[0] AS type, count(n) AS cnt ORDER BY cnt DESC")
    for r in result:
        print(f"  {r['type']}: {r['cnt']}")

    result = session.run("MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS cnt ORDER BY cnt DESC")
    print()
    for r in result:
        print(f"  →{r['type']}: {r['cnt']}")


def main():
    print("=" * 60)
    print("Миграция: JSON → Neo4j")
    print("=" * 60)
    print()

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))

    with driver.session() as session:
        clear_db(session)
        print()
        create_nodes(session, graph["nodes"])
        print()
        create_edges(session, graph["edges"])
        print()
        create_constraints(session)
        print()
        verify(session)

    driver.close()

    print()
    print("=" * 60)
    print("✓ Миграция в Neo4j завершена")
    print("=" * 60)
    print()
    print(f"Neo4j Browser: http://localhost:7474")
    print(f"Логин: neo4j / Пароль: personal2026")


if __name__ == "__main__":
    main()

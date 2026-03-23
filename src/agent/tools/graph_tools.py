"""Neo4j graph store for GraphRAG (Week 6).

Persists the file import graph as a property graph:
  (:File {path, run_id, visited, repo_path}) -[:IMPORTS]-> (:File)

Two queries power the planner:
  - query_central_files: in-degree centrality (most-imported files)
  - query_frontier_files: 1-hop unvisited neighbors of visited files

All functions are no-ops when NEO4J_URI is not set, so the agent
runs normally without Neo4j configured.
"""

import os

from neo4j import AsyncGraphDatabase, AsyncDriver

_driver: AsyncDriver | None = None


def _get_driver() -> AsyncDriver | None:
    global _driver
    uri = os.getenv("NEO4J_URI")
    if not uri:
        return None
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            uri,
            auth=(
                os.getenv("NEO4J_USERNAME", "neo4j"),
                os.getenv("NEO4J_PASSWORD", ""),
            ),
        )
    return _driver


async def sync_imports(run_id: str, repo_path: str, file_imports: dict[str, list[str]]) -> None:
    """Merge File nodes and IMPORTS edges for a batch of just-explored files.

    Marks source files as visited=true. Target files are created as stubs
    (visited=false) if they don't exist yet - the planner uses these as
    frontier candidates.
    """
    driver = _get_driver()
    if driver is None or not file_imports:
        return

    async with driver.session() as session:
        for source, targets in file_imports.items():
            await session.run(
                """
                MERGE (s:File {path: $source, run_id: $run_id})
                SET s.visited = true, s.repo_path = $repo_path
                """,
                source=source, run_id=run_id, repo_path=repo_path,
            )
            for target in targets:
                await session.run(
                    """
                    MERGE (s:File {path: $source, run_id: $run_id})
                    MERGE (t:File {path: $target, run_id: $run_id})
                    SET s.visited = true, s.repo_path = $repo_path
                    SET t.repo_path = $repo_path
                    MERGE (s)-[:IMPORTS]->(t)
                    """,
                    source=source, target=target, run_id=run_id, repo_path=repo_path,
                )


async def query_central_files(run_id: str, limit: int = 8) -> list[tuple[str, int]]:
    """Return (path, import_count) for the most-imported files, by in-degree."""
    driver = _get_driver()
    if driver is None:
        return []

    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (f:File {run_id: $run_id})<-[:IMPORTS]-()
            RETURN f.path AS path, count(*) AS import_count
            ORDER BY import_count DESC
            LIMIT $limit
            """,
            run_id=run_id, limit=limit,
        )
        return [(r["path"], r["import_count"]) async for r in result]


async def query_frontier_files(run_id: str, limit: int = 10) -> list[str]:
    """Return unvisited files that are directly imported by visited files (1-hop frontier).

    These are the highest-value targets for the next exploration iteration:
    already confirmed to be referenced by code we understand, but not yet read.
    """
    driver = _get_driver()
    if driver is None:
        return []

    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (v:File {run_id: $run_id, visited: true})-[:IMPORTS]->(u:File {run_id: $run_id})
            WHERE NOT u.visited = true
            RETURN DISTINCT u.path AS path
            LIMIT $limit
            """,
            run_id=run_id, limit=limit,
        )
        return [r["path"] async for r in result]


async def cleanup_run(run_id: str) -> None:
    """Delete all nodes and edges for a completed run to free graph memory."""
    driver = _get_driver()
    if driver is None:
        return

    async with driver.session() as session:
        await session.run(
            "MATCH (f:File {run_id: $run_id}) DETACH DELETE f",
            run_id=run_id,
        )

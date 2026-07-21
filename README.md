# Nexus — OSINT Link-Analysis on a Neo4j Knowledge Graph

Nexus turns messy public-record sanctions data (OFAC, EU, UN) into a queryable knowledge
graph, resolves entities across sources, and lets an analyst explore and annotate the
result as a force-directed network.

**Status: scaffolding only.** The repository structure and service skeletons are in
place; the end-to-end application is not functional yet.

## Quick start (once services are wired in later tasks)

```bash
cp .env.example .env          # set NEO4J_PASSWORD before continuing
docker compose up neo4j       # Neo4j Browser at http://localhost:7474
```

The three services — `api`, `ingest`, `web` — are stubbed in
[`docker-compose.yml`](./docker-compose.yml) and will be wired into the local stack as
implementation progresses.

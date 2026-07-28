#!/usr/bin/env bash

set -Eeuo pipefail

repository_root="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.."
    pwd
)"

neo4j_username="${NEO4J_USERNAME:-neo4j}"
neo4j_uri="${NEO4J_URI:-bolt://127.0.0.1:7687}"

: "${NEO4J_PASSWORD:?Export NEO4J_PASSWORD before running Neo4j scripts}"

neo4j_query() {
    if command -v cypher-shell >/dev/null 2>&1; then
        cypher-shell \
            -a "$neo4j_uri" \
            -u "$neo4j_username" \
            -p "$NEO4J_PASSWORD" \
            "$@"
        return
    fi

    docker compose \
        --project-directory "$repository_root" \
        exec -T neo4j \
        cypher-shell \
            -a bolt://127.0.0.1:7687 \
            -u "$neo4j_username" \
            -p "$NEO4J_PASSWORD" \
            "$@"
}

wait_for_neo4j() {
    local attempt

    for ((attempt = 1; attempt <= 20; attempt++)); do
        if neo4j_query "RETURN 1" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done

    echo "Neo4j did not become ready within 40 seconds." >&2
    return 1
}

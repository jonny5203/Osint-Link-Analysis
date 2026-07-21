#!/usr/bin/env bash

set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd -- "$script_dir/.." && pwd)"

source "$script_dir/lib/neo4j.sh"

wait_for_neo4j
neo4j_query < "$repository_root/api/src/main/resources/schema.cypher"
neo4j_query "CALL db.awaitIndexes(60);"

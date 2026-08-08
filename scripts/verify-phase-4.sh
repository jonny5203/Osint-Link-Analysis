#!/usr/bin/env bash

set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repository_root="$(cd -- "$script_dir/.." && pwd)"
run_dir="$(mktemp -d /tmp/nexus-phase4.XXXXXX)"
container_name="nexus-phase4-$PPID-$$"

neo4j_port="${PHASE4_NEO4J_PORT:-17687}"
api_port="${PHASE4_API_PORT:-18080}"
web_port="${PHASE4_WEB_PORT:-15173}"

for port in "$neo4j_port" "$api_port" "$web_port"; do
  if [[ ! "$port" =~ ^[0-9]+$ ]]; then
    echo "Phase 4 ports must be numeric." >&2
    exit 2
  fi
done

neo4j_password="$(openssl rand -hex 18)"
analyst_username="phase4-analyst"
analyst_password="$(openssl rand -hex 18)"
api_pid=""
web_pid=""

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM

  if [[ -n "$web_pid" ]]; then
    kill "$web_pid" 2>/dev/null || true
    wait "$web_pid" 2>/dev/null || true
  fi
  if [[ -n "$api_pid" ]]; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  docker rm -f "$container_name" >/dev/null 2>&1 || true

  if [[ $exit_code -eq 0 && "$run_dir" == /tmp/nexus-phase4.* ]]; then
    rm -rf -- "$run_dir"
  else
    echo "Phase 4 logs retained at $run_dir" >&2
  fi

  exit "$exit_code"
}
trap cleanup EXIT INT TERM

wait_for_command() {
  local description="$1"
  shift

  for _ in {1..60}; do
    if "$@" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done

  echo "$description did not become ready." >&2
  return 1
}

docker run --detach --rm \
  --name "$container_name" \
  --publish "127.0.0.1:${neo4j_port}:7687" \
  --env "NEO4J_AUTH=neo4j/${neo4j_password}" \
  neo4j:5.26.28-community@sha256:20779498e70e05772836fb980449bf691f519b42d87372e3f499312cb32c5430 \
  >"$run_dir/neo4j-container-id"

wait_for_command "Disposable Neo4j" docker exec "$container_name" \
  cypher-shell -u neo4j -p "$neo4j_password" "RETURN 1"

docker exec -i "$container_name" cypher-shell -u neo4j -p "$neo4j_password" \
  < "$repository_root/api/src/main/resources/schema.cypher"
docker exec "$container_name" cypher-shell -u neo4j -p "$neo4j_password" \
  "CALL db.awaitIndexes(60);"
docker exec -i "$container_name" cypher-shell -u neo4j -p "$neo4j_password" \
  < "$repository_root/fixtures/demo/fixture.cypher"

(
  cd "$repository_root/api"
  SPRING_NEO4J_URI="bolt://127.0.0.1:${neo4j_port}" \
  SPRING_NEO4J_USERNAME="neo4j" \
  SPRING_NEO4J_PASSWORD="$neo4j_password" \
  ANALYST_USERNAME="$analyst_username" \
  ANALYST_PASSWORD="$analyst_password" \
  ./mvnw -q spring-boot:run -Dspring-boot.run.arguments="--server.port=${api_port}"
) >"$run_dir/api.log" 2>&1 &
api_pid=$!

wait_for_command "Spring GraphQL API" curl --fail --silent --show-error \
  --user "$analyst_username:$analyst_password" \
  --header "Content-Type: application/json" \
  --data '{"query":"query { __typename }"}' \
  "http://127.0.0.1:${api_port}/graphql"

(
  cd "$repository_root/web"
  NEXUS_API_TARGET="http://127.0.0.1:${api_port}" \
  npm run dev -- --host 127.0.0.1 --port "$web_port"
) >"$run_dir/web.log" 2>&1 &
web_pid=$!

wait_for_command "Vite frontend" curl --fail --silent --show-error \
  "http://127.0.0.1:${web_port}/"

(
  cd "$repository_root/web"
  PHASE4_BASE_URL="http://127.0.0.1:${web_port}" \
  PHASE4_ANALYST_USERNAME="$analyst_username" \
  PHASE4_ANALYST_PASSWORD="$analyst_password" \
  npm run test:e2e
)

if rg --fixed-strings --quiet "$analyst_password" "$repository_root/web/dist"; then
  echo "Generated browser assets contain the runtime analyst password." >&2
  exit 1
fi

#!/usr/bin/env bash
set -Eeuo pipefail

export NEO4J_PASSWORD="${NEO4J_PASSWORD:-verification-only-password}"
export ANALYST_USERNAME="${ANALYST_USERNAME:-analyst}"
export ANALYST_PASSWORD="${ANALYST_PASSWORD:-verification-only-password}"

repository_root="$(
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
  pwd
)"

cd "$repository_root"

./api/mvnw --file api/pom.xml test

(
    cd ingest

    uv sync --frozen --python 3.13.12
    uv run --frozen python -c '
import sys
assert sys.version_info[:2] == (3, 13), sys.version
    '
    uv run --frozen ruff check .
    uv run --frozen ruff format --check .
    uv run --frozen pytest
    uv run --frozen nexus-ingest --help >/dev/null
)

(
    cd web

    npm ci
    npm run lint
    npm run test -- --run
    npm run build
)

export NEO4J_PASSWORD="${NEO4J_PASSWORD:-verification-only-password}"
export ANALYST_PASSWORD="${ANALYST_PASSWORD:-verification-only-password}"

docker compose config --quiet

images="$(docker compose config --images)"
if grep -Eq '(^|:)(latest|5)$' <<<"$images"; then
    echo "Floating Docker image found:" >&2
    echo "$images" >&2
    exit 1
fi

echo "Phase 1 verification passed."

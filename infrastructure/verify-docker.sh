#!/bin/sh
# Execute only on an isolated local Docker environment with synthetic test data.
set -eu
cd "$(dirname "$0")/.."
docker compose up -d --build --wait
docker compose exec -T backend pytest -q
docker compose exec -T backend python -m app.evaluation.run
docker compose exec -T backend python -m app.demo --synthetic-consent

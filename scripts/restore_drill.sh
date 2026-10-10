#!/usr/bin/env bash
set -euo pipefail
: "${CLIENT_ENV_FILE:?Set CLIENT_ENV_FILE}"
backup="${1:?Provide a backup filename}"
target="${2:?Provide a NEW restore-check database name}"
if [[ ! "$target" =~ ^restore_check_[a-z0-9_]+$ ]]; then echo 'Target must start with restore_check_.' >&2; exit 1; fi
test -s "$backup"
# createdb refuses an existing database. Never overwrite the active database.
docker compose --env-file "$CLIENT_ENV_FILE" -f compose.production.yaml exec -T db \
  sh -c 'createdb -U "$POSTGRES_USER" "$1"' sh "$target"
docker compose --env-file "$CLIENT_ENV_FILE" -f compose.production.yaml exec -T db \
  sh -c 'pg_restore --exit-on-error --no-owner -U "$POSTGRES_USER" -d "$1"' sh "$target" < "$backup"
echo 'Restore completed into a separate restore_check database. Run schema/data acceptance before deleting it.'

#!/usr/bin/env bash
set -euo pipefail
umask 077
: "${CLIENT_ENV_FILE:?Set CLIENT_ENV_FILE}"
destination="${1:?Provide a new backup filename}"
if [[ -e "$destination" ]]; then echo 'Refusing to overwrite an existing backup.' >&2; exit 1; fi
temporary="$(mktemp "${destination}.partial.XXXXXX")"
trap 'rm -f "$temporary"' EXIT
docker compose --env-file "$CLIENT_ENV_FILE" -f compose.production.yaml exec -T db \
  sh -c 'pg_dump --format=custom --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$temporary"
test -s "$temporary"
mv "$temporary" "$destination"
echo 'Database backup completed. Store it encrypted outside the host and verify restoration.'

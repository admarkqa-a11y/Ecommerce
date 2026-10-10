# Retail Master — backend integration release 0.3.0

Backend first. Frontend work is paused until the owner explicitly approves it.
This package contains backend source, migrations, tests, synthetic fixtures, deployment definitions and documentation. It does not contain either frontend application and requires no Node.js installation.

This is a runnable backend review milestone, **not the completed production V1**. Read `docs/backend/STATUS.md` for implemented features and remaining release gates. The original approved documents are retained under `docs/approved/` as design targets, not a claim that every planned endpoint exists.

## Stack and layout

- Python 3.12, Django 5.2, Django REST Framework; modular monolith.
- PostgreSQL 17 for deployments; SQLite only for local review and quick tests.
- Celery and Redis for background work and distributed cache/throttling.
- Cookie sessions, CSRF protection, staff TOTP and role capabilities.
- English and Arabic catalog/content fields, deployment currency and timezone, zero tax.

```text
backend/
  config/           settings, routes, HTTP composition, OpenAPI, health, Celery
  common/           errors, monetary allocation, whole-unit validation
  apps/
    identity/       users, roles, password/OTP login, staff MFA
    configuration/ runtime store settings and bootstrap commands
    catalog/        categories, brands, attributes, variants, publication
    inventory/      balances and append-only stock movements
    delivery/       methods, zones, areas and rules
    promotions/     priority and unit discount allocation
    orders/         carts, quotes, orders, snapshots, fulfillment
    payments/       collection, refunds and adapter contract
    imports/        CSV staging, validation, rollback dry run and commit
    content/        pages and predefined homepage sections
    customers/      addresses, wishlists and verified reviews
    analytics/      qualified sessions, conversion and financial reports
    operations/     audit records and durable notification retries
  tests/            business, API, security and regression checks
fixtures/           neutral roles and two fictional client datasets
scripts/            fresh-client generation and real HTTP smoke test
docs/backend/       review guide, actual endpoints, OpenAPI and status
docs/approved/      original full architecture and contracts
compose.backend.yaml
.github/workflows/backend.yml
```

## Quick local review

Run from the extracted project directory. These commands use a development SQLite database; they are not production setup instructions.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.lock
python backend/manage.py migrate
python backend/manage.py bootstrap
python backend/manage.py createadmin --email your-admin@example.com
python backend/manage.py runserver 127.0.0.1:8000
```

The admin command prompts for a password and prints a private TOTP enrollment URI. Add it to your authenticator. No default admin credentials are bundled. A staff API login requires password, `admin: true`, and a current authenticator code.

Before starting the server, optionally run `python backend/manage.py seed_demo a` for gaming/electronics or `seed_demo b` for electrical/accessories. Each demo requires a separate empty development database. Do not load both into the same database. Demo importer accounts have unusable passwords and are deactivated after seeding. Policy pages stay draft and synthetic WhatsApp numbers are disabled until configured.

Review endpoints:

- `http://127.0.0.1:8000/api/v1/health/live`
- `http://127.0.0.1:8000/api/v1/health/ready`
- `http://127.0.0.1:8000/api/v1/store/config`
- `http://127.0.0.1:8000/api/v1/store/products`
- `http://127.0.0.1:8000/api/v1/schema`
- `http://127.0.0.1:8000/api/v1/docs` (Swagger's display assets require Internet access)

The checked-in `docs/backend/openapi.yaml` can also be imported into an API client. Action responses containing dynamic attributes use open-ended JSON schemas; do not mistake them for fully typed frontend client contracts.

## Run verification without a frontend

```bash
python -m pytest backend
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run
python backend/manage.py spectacular --file /tmp/retail-openapi.yaml --validate --fail-on-warn
python scripts/backend_smoke.py
```

The smoke script creates a disposable database, runs a loopback HTTP server, exercises a real guest checkout, and removes the database afterwards. It explicitly ignores deployment database/queue/email configuration. The PostgreSQL concurrency test skips on SQLite; use PostgreSQL CI or the deployment database engine for that release gate.

## Backend-only PostgreSQL/Redis review stack

Docker and Docker Compose are required. No frontend containers are started.

```bash
python3 scripts/new_backend_client.py demo-a --port 8000
export CLIENT_ENV_FILE=client-deployments/demo-a/.env
docker compose --env-file "$CLIENT_ENV_FILE" -f compose.backend.yaml up --build -d
docker compose --env-file "$CLIENT_ENV_FILE" -f compose.backend.yaml exec api python manage.py createadmin --email your-admin@example.com
```

The environment generator writes fresh private secrets and refuses to overwrite an existing client directory. Compose loads those values for both interpolation and application containers. The API binds to loopback; PostgreSQL/Redis have no host port exposure. Each project has separate database, media and queue volumes. The supplied stack uses development HTTP settings for local review. Production needs reviewed HTTPS ingress, production environment settings, external secret management, private storage, backup/restore and monitoring.

## BUILD ONCE → CLONE → CONFIGURE → LAUNCH

1. Freeze one tested master release and build the API image once. Record its immutable digest.
2. Generate a new client environment; provision separate database, Redis, media, credentials and domains. Never restore another client's production database.
3. Deploy the same release image/digest; run migrations and the neutral `bootstrap` command.
4. Create that client's admin interactively. Configure business identity, currency, languages, delivery, content, WhatsApp and enabled payment methods through client data/settings.
5. Create client-specific attribute definitions and dependencies, then upload/preview/confirm the client's CSV. Do not put client product rules into source code.
6. Complete backend release gates and two-client isolation checks before launch. Frontend implementation remains separately gated by the owner's instruction.

To review Client B locally, use `new_backend_client.py demo-b --port 8002`, then its own `CLIENT_ENV_FILE`. Both Compose projects reference the same release image tag. Production promotion must pin the same digest and demonstrate isolation; those deployment checks have not yet been executed here.

SkipCash is the selected card provider. The adapter, signed webhooks and reconciliation are implemented, but real merchant sandbox verification is outstanding. Card payments default to disabled. Read `SKIPCASH.md` before enabling them. Production-oriented configuration and cloning commands are in `DEPLOYMENT.md`; this release is not yet certified production-ready.

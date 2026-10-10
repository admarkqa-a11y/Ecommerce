# Verification — backend 0.3.0

Executed 5 October 2026, Python 3.12 / Django 5.2.17, isolated local SQLite test database.

| Check | Result |
|---|---|
| Automated backend suite | 72 passed, 4 skipped; final run 26.62 seconds |
| Django system check | Passed, no issues |
| Migration drift | Passed, no changes detected |
| OpenAPI generation/validation, fail-on-warn | Passed |
| Production-settings static check, fail-level WARNING | Passed using generated dummy configuration; no database/provider connection |
| Real loopback HTTP smoke | Passed readiness, CSRF, catalog, cart, quote, COD checkout, idempotency, zero tax, guest ownership |
| Compose/CI YAML parsing | Passed; not Docker execution |
| Backup/restore shell syntax | Passed; not a real restore |
| Git whitespace check | Passed |

Coverage includes promotion bundles/BXGY/customer limits, original-price refunds, analytics consent/cohorts, SkipCash HMAC and mocked transport, payment replay/unknown/mismatch/late capture, customer password/session behavior, addresses, typed attributes, Arabic search and durable outbox retries. Mocked provider tests establish local behavior only.

Four tests require PostgreSQL and skipped here: reservation oversell, simultaneous checkout idempotency, customer coupon limit race and concurrent outbox claims. CI includes PostgreSQL and two-client Docker verification, but no successful CI run is claimed. Docker/PostgreSQL service execution was unavailable in this environment. No live gateway, merchant sandbox, SMTP, public domain/TLS, Caddy runtime, actual container image or real backup restoration was verified.

The remaining implementation scope and release gates are in STATUS.md. This release must not be represented as completed production V1 solely because these checks passed.

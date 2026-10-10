# Deployment and client cloning

This runbook is for target-host verification of 0.3.0. Successful startup does not certify the remaining V1 scope. Use a staging deployment first.

## Prerequisites

Linux host with Docker/Compose, DNS pointed at the host, ports 80/443 available, registry access, SMTP and secrets configured securely. No secrets are bundled. The production Compose stack allocates host ports 80/443; use separate hosts/IPs per client, or deliberately configure a shared routing ingress. Multiple unchanged production stacks cannot bind those ports on one host.

Build `backend/Dockerfile` with repository root as context, push to your registry, and record the immutable digest. Build once and reuse that exact digest for every client. PostgreSQL/Redis/Caddy versions in Compose are major-version tags; pin reviewed dependency image digests in your operational release process.

```bash
docker build -f backend/Dockerfile -t REGISTRY/retail-backend:0.3.0 .
docker push REGISTRY/retail-backend:0.3.0
python3 scripts/new_production_client.py client-a --domain api.CLIENT-DOMAIN --tls-email OPERATOR-EMAIL --image REGISTRY/retail-backend@sha256:ACTUAL_DIGEST
export CLIENT_ENV_FILE=client-deployments/client-a/.env
```

Replace placeholders with actual values. Generator validates the digest and hostname and refuses overwrites. Configure SMTP sender/credentials, customer origin, allowed CSRF origins and optionally the approved SkipCash merchant environment in the private environment file. Keep secrets outside version control and use a secret manager in your hosting workflow. Customer/admin browser origin integration must be verified when those applications exist.

```bash
docker compose --env-file "$CLIENT_ENV_FILE" -f compose.production.yaml up -d
docker compose --env-file "$CLIENT_ENV_FILE" -f compose.production.yaml exec api python manage.py createadmin --email YOUR-ADMIN-EMAIL
docker compose --env-file "$CLIENT_ENV_FILE" -f compose.production.yaml exec api python manage.py check --deploy --fail-level WARNING
docker compose --env-file "$CLIENT_ENV_FILE" -f compose.production.yaml exec api python manage.py deployment_check
```

Use `deployment_check --require-card` when card configuration is enabled. This checks configuration and infrastructure, not real payment success. Enroll the admin TOTP privately. Configure store settings and client-owned catalog/delivery/content, then validate/preview/confirm the client's CSV. Seed demos only into disposable databases, never real client deployments.

## Isolation acceptance

Run `python scripts/verify_two_clients.py` on a Docker-capable test host. It builds one image, starts two disposable PostgreSQL/Redis stacks, loads different synthetic configurations, compares actual image IDs, checks mutation isolation and runs a separate database restore drill. It removes only its generated test projects. Review this script before running on a host with other workloads. The production domain/TLS path is a separate acceptance test.

Each clone must have a fresh database, media volume, queue/cache, encryption key, session secrets, admin enrollment, SMTP/payment credentials and domain. Never clone a production database. Configuration and safe synthetic fixtures are the only reusable business inputs. Future updates deploy the same reviewed image with per-client migrations and backups; clients do not fork core code.

## Backup and recovery

```bash
bash scripts/backup_backend.sh /SECURE-PATH/client-a.dump
bash scripts/restore_drill.sh /SECURE-PATH/client-a.dump restore_check_release03
```

Backup script refuses an existing filename; restore requires a new restore_check database and never overwrites the live database. Verify restored counts, constraints and application reads. Encrypt backups off-host and establish retention/RPO/RTO. Media volume and field-encryption keys need separate protected backup; the database script does not back up media or keys. Establish PostgreSQL PITR if required. No automatic disaster recovery is claimed.

Monitor readiness, queue age, failed notification attempts, unknown/exception card attempts, unmatched provider refunds, expired reservations, database space and backup age. Unknown card outcomes must be investigated before releasing reserved stock. Do not restart payment creation blindly.

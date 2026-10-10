# Client deployment and cloning

This is a deployment blueprint with runnable local Compose definitions, not evidence of an executed production deployment.

1. Complete the release gates in IMPLEMENTATION_STATUS.md and run the full PostgreSQL/browser/provider acceptance suite.
2. Build API, storefront and admin once; assign an immutable release tag and record all image digests. The worker/scheduler use the API image. Never bake a client identity, domain, payment key or customer record into an image.
3. For each client, allocate a fresh database/user, media bucket or enforced IAM prefix, Redis service, domains, secret-encryption key, Django key, staff identities, email sender and payment merchant credentials.
4. Run `scripts/new_client.py` to create an initial private local environment. Replace local settings with production hostnames, HTTPS trusted origins, production email and protected secret references. Keep this private manifest out of the master Git tree.
5. Replace build directives with the selected release's image digests in the production manifest. Set ENVIRONMENT=production and use PostgreSQL DATABASE_URL. Never carry development SQLite or demo importer accounts into a client.
6. Run migrations/bootstrap once. Create the Super Admin interactively; enroll TOTP and rotate any bootstrap access. Import the client's approved catalog/configuration into the empty database.
7. Configure TLS at a trusted reverse proxy. The included nginx.local.conf is HTTP-only for local use; it is not a production TLS template. Set Host and X-Forwarded-Proto correctly and do not trust unvalidated public proxy headers. Storefront/admin should be separate hostnames with host-only cookies.
8. Configure public media and private invoices/imports separately. The current release's local file setup must be replaced by the reviewed storage adapter before production.
9. Validate backup/restore, worker/scheduler uniqueness, payment callbacks and replay, secret rotation, monitoring, email deliverability, English/Arabic, staff roles and customer ownership.
10. Record the client release/schema/config versions and operator contacts. Launch only after the release gates pass.

**No production database cloning**

Cloning creates a new installation from the master release. It never duplicates a trading client's database, media, sessions, staff users, merchant references, orders or customer records. Demo packs are intentionally separate from neutral bootstrap defaults and are forbidden outside development.

**Local two-install exercise**

Generate two private environment files with different slugs and ports. For each invocation, set CLIENT_ENV_FILE to that client's absolute environment path and pass the same path to `docker compose --env-file`. The Compose project name controls separate volumes. Do not reuse the other client's database URL or volumes. Use demo A in one and demo B in the other, only in development. Replace build directives with the exact same image digests when conducting release acceptance.

**Upgrade**

Back up and verify restoration, test the new master release in isolated staging, apply reviewed migrations, deploy the new images and run smoke checks. Keep database changes backward-compatible where possible. A code rollback does not undo a database migration. Database restoration requires an explicit recovery procedure; never delete or recreate a client's volumes as an upgrade technique.


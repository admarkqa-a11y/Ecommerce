# Frontend setup — 0.4.1

Separate customer storefront and admin application, integrated with the backend in this package. Use Node.js 24, npm and Python 3.12. PostgreSQL 17 and Redis are deployment dependencies; SQLite is for disposable local review only.

For the marketplace design changes and optional client colors, see MARKETPLACE_UPDATE.md.

## Local review

From the extracted project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.lock
python backend/manage.py migrate
python backend/manage.py bootstrap
python backend/manage.py seed_demo a
python backend/manage.py createadmin --email YOUR-ADMIN-EMAIL
python backend/manage.py runserver 127.0.0.1:8000
```

The admin command asks for a password and provides a private authenticator enrollment URI. No default staff login is included. Never share enrollment secrets. Demo `b` is the electrical/accessories dataset; use a separate empty database. These demo settings are synthetic, and policy pages remain unpublished until approved content is supplied.

In another terminal:

```bash
npm ci
npm run dev:storefront
```

In a third terminal:

```bash
npm run dev:admin
```

Open `http://localhost:3000/en` or `/ar`; admin is `http://localhost:3001`. The API origin defaults to `http://127.0.0.1:8000` and can be set through server-side `API_ORIGIN`. Django must trust the actual storefront/admin origins for CSRF. If using `127.0.0.1` in browser URLs, explicitly add those origins to `CSRF_TRUSTED_ORIGINS` before starting the backend.

Local ports on the same hostname share cookie scope. Use separate browser profiles for simultaneous customer/admin local review; production uses separate hostnames with host-only cookies.

## Verify and build

```bash
npm run typecheck
npm run test:frontend
npm run build
python scripts/verify_frontend.py --demo a
python scripts/verify_frontend.py --demo b
```

The last two commands provision disposable SQLite databases, start the built applications on loopback ports 3100/3101 with an API on 8100, create synthetic COD orders and test an ephemeral admin account. They remove their database and stop their servers. They never use an existing deployment database or SMTP configuration. No real card charge is attempted. Those ports must be available.

`test:frontend` is a jsdom component test, not visual browser verification. `verify_frontend.py` tests live HTTP and API integration, not browser clicks. See VERIFICATION.md for exact results and outstanding checks.

For local production-build review, `npm run start --workspace @retail/storefront` and the corresponding admin command can serve the built apps. Deployment uses the standalone server in the Dockerfile. `API_ORIGIN` remains runtime configuration; there are no client-specific public environment variables baked into browser bundles.

## Admin onboarding

1. Sign in using staff password and authenticator code.
2. Configure business name, English/Arabic text, colors, logo URL, currency and contacts in Settings. Currency changes lock after transactions exist.
3. Create categories, brands, attribute definitions and options; create products and variants. Assign descriptive values using the product Attributes action. Publish explicitly.
4. Configure delivery methods, areas and rules. Use the CSV screen to upload, inspect errors, run dry run and confirm the whole file.
5. Configure predefined homepage sections, positions, schedules and bilingual content, then publish them. The storefront renders published enabled sections in their configured order.
6. Review orders, collections/refunds and separate stock returns. Check reporting, uncertain card attempts and notification retries.

Advanced rule/property fields currently use validated JSON editors. Staff must understand the documented backend contract for those fields; a complete guided rule builder is not included.

## Hosting and cloning

See DEPLOYMENT.md. Build one backend, one storefront and one admin image. Use the same three digests for every client with completely separate databases, volumes, secrets, users, domains and settings. Never copy a client's live database to provision another client.

# Marketplace verification — 0.4.1

6 October 2026. This report covers the storefront redesign; historical backend results are not represented as new runs.

Passed:

- Storefront TypeScript check and optimized Next.js production build.
- Existing component checks: reports, Arabic empty states, checkout quotation, hosted-card handoff, order idempotency key, disabled gateway visibility, and read-only admin navigation.
- New marketplace component checks: runtime header contrast for bright/dark colors, unsafe hero image rejection, CMS section ordering, localized category links, typed search input and URL submission, same-route query updates, real sale percentage calculation, and Arabic direction.
- Two independent disposable client configurations (A and B) using the same built frontend: English/Arabic server rendering; catalog/product detail and 404 handling; URL-based search and empty results; category navigation and homepage markup; Next API proxy cookies and CSRF; cart, delivery quote, COD order, idempotent retry, guest-order isolation; staff password/TOTP login, reports, resource permissions, operational endpoints, and runtime brand-name changes.
- Source diff whitespace check and ZIP integrity/content checks.

The first integration attempt encountered a native cryptography import crash in the local environment. Reinstalling the same locked version, cryptography 50.0.2, resolved it. Both client runs then passed; no dependency pin or application security behavior was changed.

Not verified:

- Real-browser desktop/mobile/RTL screenshots, visual layout, keyboard/screen-reader behavior and browser interaction acceptance. Chromium startup failed because the environment blocks the process singleton socket. jsdom and HTTP checks are not substitutes for these.
- Live card processing, PostgreSQL concurrency, Docker/TLS production deployment, and the outstanding full-V1 features listed in STATUS.md and ../backend/STATUS.md.

Commands:

```
npm run typecheck --workspace @retail/storefront
npm run test:frontend
npm run build --workspace @retail/storefront
python scripts/verify_frontend.py --demo a
python scripts/verify_frontend.py --demo b
```

Optional `--snapshot-dir PATH` on the integration script writes English/Arabic server-rendered HTML for design review from the disposable seed data. These are static markup snapshots, not screenshots or functional standalone applications.

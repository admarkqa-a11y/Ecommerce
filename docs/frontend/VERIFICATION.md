# Verification record — 0.4.0

Executed locally on 5 October 2026 using Node 24, Next.js 16.3.8, React 19.3.0, Python 3.12 and the bundled backend.

| Check | Result and boundary |
|---|---|
| TypeScript, both applications | Passed |
| Optimized Next.js builds, both applications | Passed |
| jsdom component interaction checks | Passed report contract/Arabic empty state, checkout quote/card handoff, idempotency key, gateway visibility and read-only admin navigation/RTL |
| Live HTTP frontend/backend checks, Demo A | Passed on a disposable SQLite backend |
| Live HTTP frontend/backend checks, Demo B | Passed using the same already-built frontend artifacts with a separate disposable database |
| HTTP scenarios | EN/AR HTML and RTL, catalog markup, missing-page 404, admin shell, proxy session cookies/CSRF, consent, cart, quote, COD order, retry idempotency, guest ownership |
| Admin integration scenarios | Password + real TOTP, schema/capability contract, reporting, payment/notification lists, runtime branding reflected by the same frontend build |
| Backend regression suite | 72 passed, 4 PostgreSQL-only tests skipped |

The demo tests reuse built source artifacts, not Docker images. They do not certify the final requirement for two separate production deployments using identical image digests. Their database, test admin and order data are disposable; no production credentials or merchant charge was used.

Not executed successfully: Chromium visual/interaction checks (startup failed with an environment socket permission error), Docker builds/runtime, Caddy/TLS public domains, PostgreSQL concurrency, real SMTP, live/sandbox SkipCash transactions, accessibility audit, mobile device testing or full SOW acceptance. Browser installation succeeded through an official download route, but execution was restricted; no browser screenshots are included.

Reproduce component tests with `npm run test:frontend`. Reproduce HTTP integration with `python scripts/verify_frontend.py --demo a` and `--demo b` after `npm run build`. A CI definition is included; no remote CI execution is claimed.

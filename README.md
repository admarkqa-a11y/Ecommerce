# Retail Master — storefront + admin integration release 0.4.1

BUILD ONCE → CLONE → CONFIGURE → LAUNCH

This package contains the customer storefront, separate admin frontend and existing Django backend. Frontend implementation is now authorized and included. The historical backend 0.3 documents retain their original release context.

**New in this release:** the approved marketplace storefront design. See `docs/frontend/MARKETPLACE_UPDATE.md` for client configuration and `docs/frontend/VERIFICATION_0.4.1.md` for the latest checks.

**Start with `docs/frontend/START_HERE.md`.** Features and remaining limits are in `docs/frontend/STATUS.md`; executed evidence is in `docs/frontend/VERIFICATION.md`. This is a runnable source release, not certification that the entire approved V1 scope or production launch is complete.

- `apps/storefront`: Next.js storefront, English/Arabic and RTL.
- `apps/admin`: Next.js admin application with permission-aware navigation.
- `packages`: shared API, UI, translations and retry helpers.
- `backend`: Django/DRF modular commerce backend; PostgreSQL for deployment.
- `fixtures`: synthetic A/B client configuration and CSV products; no live client data.
- `deployment`, `compose*.yaml`: local stacks and production-oriented deployment definitions.
- `scripts`: client generation, integration checks and backup/restore helpers.
- `docs/approved`: original architecture/design targets, not implementation claims.

No credentials, production database, node_modules or compiled build artifacts are included. Install locked dependencies and build on your target toolchain. Client identity and commerce data remain runtime configuration.

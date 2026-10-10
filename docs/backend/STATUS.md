# Backend status — 0.3.0

5 October 2026. Backend only; frontend remains paused.

This is an integration release with production-oriented deployment definitions, not completed production V1. No real merchant payment or PostgreSQL deployment was executed here.

## Implemented

- Modular Django/DRF backend, session/CSRF, capability roles, encrypted staff TOTP, customer password recovery/change and bounded staff/customer sessions.
- Runtime white-label configuration, bilingual catalog/content, configurable currency/timezone and zero tax. Currency locks after the first order.
- Typed attributes, variants, unique SKU/combinations, publication snapshots, Arabic-normalized search, pagination, parent categories and variant-aware filtering.
- Whole-unit stock ledger, reservations, commitments, explicit departure/restock, no backorders.
- Guest/customer carts, authoritative quotes, idempotent placement, order snapshots and guarded transitions; owned saved addresses.
- COD/bank collection, SkipCash creation/status/signature adapter, durable payment attempts, signed webhook reconciliation, amount/currency/reference validation and late-payment exception handling.
- Full/partial refunds, original-unit allocations and delivery refunds, manual verified provider refund recording, separate restock.
- All requested promotion types represented; explicit bundles, separate BXGY scopes, priorities, eligibility and customer limits, allocation trace and preview.
- Configurable delivery methods/areas/days/cutoffs/minimum/free threshold and nonoverlapping value bands.
- Atomic CSV staging, validation, preview, rollback dry run, confirmation hash and error reports. Image URL ingestion remains unsupported and blocks nonempty values.
- Bilingual pages/predefined homepage sections, wishlist and review moderation.
- Consent-based qualified sessions, product/cart/checkout/purchase events, conversion cohorts, sales/revenue/customers/best-seller/stock/date/category/brand reports.
- Durable email outbox claims, retry/backoff, bilingual order/refund notifications and admin retry controls.
- Fresh-client environment generators, separate Compose volumes and credentials, immutable application image reference, HTTPS proxy definition, database backup/restore scripts, two-client image/isolation/restore verification script and PostgreSQL CI jobs.

## Remaining work before full V1 completion

The approved design documents are targets; they are not implementation evidence. Remaining internal work includes configuration revision publication/rollback, richer content scheduling/revisions/navigation, attribute sets and media workflows, complete CSV clear/replace semantics and image ingestion, cart merge/guest re-entry/policy snapshots, immutable issued PDF invoices, comprehensive promotion overlap acceptance, analytics retention, staff invitation/recovery and other identity flows from the original design. Search currently prioritizes correctness over large-catalog performance. Some list endpoints have fixed result caps and action schemas remain open-ended JSON.

Actual target release gates: PostgreSQL concurrency tests; Docker image build/start; two separate deployments using exactly the same image; backup restore and media recovery; current SkipCash contract verification plus merchant sandbox creation/payment/replay/failure/timeout/refund reconciliation; SMTP delivery; TLS/domain/cookie integration; security, load and operational alert checks. Those gates cannot be replaced by SQLite tests or mocked HTTP.

## V1 exclusions retained

Tax, multi-currency checkout, multiple warehouses, fractional units, backorders, supplier/purchase management, customer self-service returns/exchanges, WhatsApp API and unrestricted page builder are excluded. No frontend work is included. Clients never share databases, media, orders, customers, credentials or admins. Client-specific products, attributes, branding, delivery and content are data, not source changes.

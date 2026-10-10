# Backend API review guide

Base path: `/api/v1`. No trailing slash is used for application endpoints.
`API_ENDPOINTS_IMPLEMENTED.md` lists current route templates; `openapi.yaml` describes current resource fields. The much larger list under `docs/approved/` remains the complete design target.

## Authentication and permissions

Use a cookie-aware API client. First GET `/auth/csrf`; preserve its cookie and send the returned `csrfToken` as `X-CSRFToken` for unsafe methods, including guest cart and checkout. Sign-in rotates the CSRF token, so GET `/auth/csrf` again after login. Send the header as well as the cookie; supplying only one is insufficient.

POST `/auth/login`:

```json
{"email":"your-admin@example.com","password":"YOUR_PASSWORD","admin":true,"otp":"CURRENT_TOTP"}
```

Create the first admin using the interactive `createadmin` command. There are no shared seeded credentials. Staff API calls require an active staff user, an MFA-verified session, and the action's capability. Customer login omits `admin` and cannot gain staff privileges through role fields in the request. POST `/auth/logout` ends the session. GET/PATCH `/auth/session` reads/updates the caller's basic profile. Customer registration and email OTP routes are documented in the endpoint list.

Development OTP delivery uses the console email backend; configure authenticated email delivery before real usage. Never distribute development email logs or admin enrollment URIs.

| Endpoint family | Read capability | Write/action capability |
|---|---|---|
| products, categories, brands, attributes, attribute-options, variants | catalog.view | catalog.manage; publication requires catalog.publish |
| Variant cost values and cost-bearing imports | catalog.cost in addition to the resource capability | catalog.cost |
| delivery-zones, delivery-areas, delivery-methods, delivery-rules | delivery.view | delivery.manage |
| promotions | promotions.view | promotions.manage |
| pages, homepage-sections | content.view | content.manage; publication requires content.publish |
| roles | roles.manage | roles.manage; cannot grant capabilities the actor does not hold |
| reviews | reviews.moderate | reviews.moderate |
| settings | settings.view | settings.manage |
| dashboard | dashboard.view | No mutation |
| inventory | inventory.view | inventory.adjust |
| orders | orders.view | orders.transition or orders.cancel |
| order collect | — | payments.collect for COD; payments.verify_bank for bank |
| order refund and refund confirm | — | payments.refund |
| order restock | — | inventory.adjust |
| imports | imports.manage | imports.manage plus catalog.cost/catalog.publish/inventory.adjust when applicable |

Customer/guest order and invoice endpoints filter ownership; another guest's UUID does not confer access. A staff invoice request requires `documents.view` and an MFA session. Catalog responses use published snapshots and exclude cost prices.

## Catalog and dynamic variants

Admin resources live at `/admin/{resource}` and `/admin/{resource}/{uuid}`. List supports DRF page pagination. Resource GET/POST/PUT/PATCH/DELETE follow their capabilities. Products/variants are archived/deactivated on DELETE rather than deleting transaction history. Creating a variant uses the explicit action below; the generic variants POST rejects direct creation.

1. Create categories, brand and typed attribute definitions/options.
2. Create a simple or variable product through `/admin/products`.
3. POST `/admin/products/{product_id}/variants`:

```json
{"sku":"ITEM-BLACK","price":"100.00","stock":10,"options":{"color":"black"}}
```

Simple products use `options: {}`. A variable product selects one existing option for each axis. Its axes cannot silently change when adding another variant. Quantity is an integer. `cost_price` needs cost permission and nonzero opening stock needs inventory-adjust permission on this action.

4. POST `/admin/products/{product_id}/publish`. Arabic name and an active variant are required. Draft edits remain private until publication.

Public product routes are `/store/products` and `/store/products/{code}`. Current search supports q, category, brand, min_price, max_price, in_stock and `attr.{code}` filters. The current public list is capped at 100; full pagination/facets remain outstanding. Public resource values for `/store/{resource}` are `categories`, `brands`, `delivery-methods`, `delivery-areas` only.

## Checkout and stock state

POST `/cart` with `{"variant_id":"UUID","quantity":2}` adds whole units; PATCH sets a quantity; DELETE with `{"item_id":"UUID"}` removes a line. PATCH with `{"coupon":"CODE"}` updates the coupon.

POST `/checkout/quote` with `{"method_id":"UUID","area_id":"UUID"}`. Omit area for pickup. The backend calculates published prices, promotions and delivery. Tax is zero. The quote has a ten-minute validity window and binds cart version, settings and calculated totals.

POST `/checkout/orders` with an `Idempotency-Key` header and:

```json
{
  "quote_id":"UUID",
  "payment_method":"cod",
  "contact":{"name":"Buyer","email":"buyer@example.com","phone":"BUYER_PHONE"},
  "address":{"line1":"DELIVERY_ADDRESS"}
}
```

Supported payment method codes are `cod` and `bank` when enabled. Pickup does not require `address.line1`. Card is rejected until a real adapter is installed. Never send or trust client-calculated totals. Reusing the same idempotency key with different input gives a conflict; stale quote/cart data gives a conflict and requires a new quote.

- Bank pending: reserve stock. Verification commits it and accepts the order.
- COD: reserve and accept immediately, moving reservation to commitment.
- Dispatch/collection: reduce physical on-hand and commitment once.
- Cancel before departure: release the existing reservation/commitment; do not increase physical stock.
- Refund: money ledger only. Returning inventory requires a separate bounded restock action.

## Order/payment commands

POST `/admin/orders/{id}/{command}`; use `Idempotency-Key` for collect, refund and restock:

| Command | Body |
|---|---|
| transition | `{"action":"ready_for_pickup","reason":"..."}`; also shipped, delivered, collected, cancel as state permits |
| collect | `{"reference":"VERIFIED_BANK_OR_CASH_REFERENCE"}` |
| refund | `{"amount":"25.00","reason":"Approved partial refund"}` |
| restock | `{"item_id":"UUID","quantity":1}` |

POST `/admin/refunds/{refund_id}/confirm` with `{"reference":"ACTUAL_EXTERNAL_REFUND_REFERENCE"}` only after money has actually been returned. This is offline bookkeeping, not a live provider refund. Pending/succeeded/unknown refund amounts consume available refundable headroom. Full refund before departure requires cancelling the unfulfilled order first. Refunds and fulfillment history appear in the authorized order response.

The printed HTML invoice endpoint is not an immutable legally issued PDF/document-number workflow; that remains outstanding.

## CSV import and dry run

1. POST multipart `/admin/imports` with `file`, `mode=create|update|upsert`, and `stock_mode=preserve_existing|replace_on_hand`.
2. Inspect returned rows/errors, state, dependencies and `plan_hash`. Validation runs the real commit logic inside a savepoint that is rolled back. An invalid row leaves every product/stock row unchanged.
3. POST `/admin/imports/{id}/dry-run` or `/validate` to revalidate before confirmation.
4. GET `/admin/imports/{id}/errors` for a downloadable error CSV.
5. POST `/admin/imports/{id}/confirm` with `{"plan_hash":"THE_REVIEWED_HASH"}`. All rows commit in one transaction or none do. Stale catalog/inventory invalidates the preview. Permissions are rechecked.

Full columns and bilingual samples are under `docs/approved/IMPORT_FORMAT.md` and `fixtures/products_client_a.csv`, `fixtures/products_client_b.csv`. Category/brand/attribute definitions must exist first; corresponding demo seeding sets them up. Missing cost uses null. New variants require explicit opening stock, including zero. No client database is imported.

Limits: UTF-8/BOM, 10 MiB, 5,000 rows; unknown/duplicate headers block upload. Nonempty image URLs currently block the file because safe remote-image ingestion is not yet implemented. Existing blank optional text/brand values preserve current values; price/sale/cost have limited preserve/null handling. The full approved clear/replace semantics and before/after preview are not yet delivered. GET import list returns safe summaries; cost-bearing details require cost permission.

## Configuration, content and analytics

GET/PATCH `/admin/settings` manages runtime settings. Transaction currency is locked after the first order. Currency migration must be a controlled operation; no endpoint bypasses that restriction. Public settings expose an allowlist and `tax_mode: disabled`.

Content publication allows only `/admin/pages/{id}/publish` and `/admin/homepage-sections/{id}/publish`, with content-publish permission. Homepage sections use predefined types. Public data is at `/store/homepage` and `/store/pages/{slug}`.

GET `/admin/dashboard?from=YYYY-MM-DD&to=YYYY-MM-DD` uses the store timezone and a maximum 366-day range. Reports include accepted sales, captures minus successful refunds by ledger date, purchasing customers, low stock, best sellers and sales by date/category/brand using order snapshots. Conversion is accepted purchases attributable within seven days / qualified shopping sessions in the selected cohort. Cohorts may remain provisional; a session can buy more than once, so the ratio can exceed 100%. No sessions gives null, not a fabricated zero. Staff, bots and test deployments do not qualify. Analytics requires consent; session inactivity timeout is 30 minutes.

## Errors and review boundaries

400: validation failure; 403: missing authorization/CSRF; 404: unavailable or unowned resource; 409: stale state/idempotency/relationship conflict; 429: throttle. Error bodies currently vary between standard DRF field errors and domain code/detail errors. Health readiness reports generic 503 without infrastructure credentials.

See `STATUS.md` for every major remaining V1 module and `VERIFICATION.md` for executed evidence. Do not approve a production launch solely from successful local tests.


## Added in 0.3

- POST `/analytics/consent` and `/analytics/product-view`: consent-based shopping sessions and deduplicated views; cart, checkout and purchase events are server-generated.
- GET `/store/bundles`; POST/DELETE `/cart/bundles`: explicitly selected fixed-price component bundles. Ordinary component purchases do not automatically become a bundle.
- POST `/admin/promotions/preview`: privileged calculation trace. Per-customer eligibility/redemption limits, separate BXGY qualifier/reward scopes and priority allocation are supported.
- GET `/admin/payment-attempts`; POST `/admin/payment-attempts/{id}/reconcile`: payments.view / payments.reconcile. Card status is determined by the provider, never by the browser redirect. See SKIPCASH.md.
- GET `/admin/notifications`; POST `/admin/notifications/{id}/retry`: operations.manage; delivered events cannot be manually resent. SMTP is at-least-once, with eight attempts and bounded exponential retry.
- GET/POST `/account/addresses`; GET/PATCH/DELETE `/account/addresses/{id}`: authenticated owner only. Checkout may pass an owned `address_id`.
- GET/PUT/PATCH `/admin/products/{id}/attributes`: typed descriptive values; PUT replaces, PATCH updates. Publish explicitly after edits.
- POST `/auth/password/reset-request`, `/auth/password/reset-confirm`, `/auth/password/change`: customer reset links expire after 15 minutes; password changes invalidate old sessions. Staff recovery is not implemented.

Item refunds support original order-item quantities and optional delivery amount; amounts are derived from frozen net unit allocations. Pending allocations consume refundable capacity. A refund never restocks inventory. SkipCash refunds require actual merchant-portal execution and verified admin recording.

Promotion priority defaults: bundle 800, BXGY 700, flash 600, deal 500, product 400, category 300, brand 200, coupon 100. Higher priority wins; allocation prevents repeated discounts on a unit. Stable tie breaking and calculation traces are persisted. Bundle remainder amounts use largest-remainder allocation. BXGY uses disjoint qualifying/reward units and cheapest eligible rewards. Held coupon redemptions release when an unpaid pending order is cancelled; accepted-order refunds do not restore usage. Full overlap acceptance remains a release gate.

Tax is explicitly disabled and zero throughout V1. This is the requested product configuration, not a legal determination. Transaction currency is deployment configuration, default QAR; the current SkipCash adapter only supports QAR.

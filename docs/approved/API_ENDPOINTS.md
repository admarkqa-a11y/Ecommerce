# Version 1 complete API endpoint inventory

**345 method/path combinations.** Paths are literal templates; each row denotes one endpoint. IDs/slugs are resolved only within the current deployment. Permissions refer to PERMISSION_MATRIX.md. This is a design inventory; production OpenAPI request/response schemas will be generated during implementation and checked against it.

Translated CRUD resource bodies contain a locale-keyed `translations` object; no parallel endpoint per language. Product/category/brand publication, financial actions and stock changes are explicit commands. Generic PATCH cannot bypass those commands. Read endpoints are paginated where applicable. DELETE archives referenced domain records.

Catalog write endpoints enforce catalog.cost on any cost field in addition to catalog.manage. Import confirmation enforces catalog.cost/inventory.adjust where relevant. Unpaid COD completion additionally requires orders.complete_unpaid. Sensitive actions require recent staff reauthentication.

Storefront-owned routes outside this API: `/[locale]/...` pages, localized `/sitemap.xml` index/shards, `/robots.txt`, favicon/assets, `/admin` frontend routes on the admin host. These are HTTP frontend resources, not missing REST endpoints. SEO resources read only published content. No browser-accessible metrics or database-management endpoint exists.

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `/api/v1/store/config` | Public | Public allowlisted runtime settings |
| GET | `/api/v1/store/homepage` | Public | Published scheduled homepage for locale |
| GET | `/api/v1/store/navigation` | Public | Published menus |
| GET | `/api/v1/store/products` | Public | Published product search, filters, sort and pagination |
| GET | `/api/v1/store/products/{slug}` | Public | Product, variants/options and current price display |
| GET | `/api/v1/store/facets` | Public | Data-driven category/brand/price/availability/attribute facets |
| GET | `/api/v1/store/categories` | Public | Category hierarchy |
| GET | `/api/v1/store/categories/{slug}` | Public | Category detail |
| GET | `/api/v1/store/brands` | Public | Brand list |
| GET | `/api/v1/store/brands/{slug}` | Public | Brand detail |
| GET | `/api/v1/store/collections` | Public | Published collections |
| GET | `/api/v1/store/collections/{slug}` | Public | Collection and products |
| GET | `/api/v1/store/offers` | Public | Eligible public offers |
| GET | `/api/v1/store/deals` | Public | Scheduled deals and flash sales |
| GET | `/api/v1/store/bundles/{id}` | Public | Bundle components and availability |
| GET | `/api/v1/store/products/{id}/reviews` | Public | Approved paginated reviews |
| GET | `/api/v1/store/compare` | Public | Bounded product IDs and comparable attribute union |
| GET | `/api/v1/store/pages/{slug}` | Public | Published localized CMS/policy page |
| GET | `/api/v1/store/blog/posts` | Public | Published posts, category/tag filters |
| GET | `/api/v1/store/blog/posts/{slug}` | Public | Localized blog detail |
| GET | `/api/v1/store/blog/categories` | Public | Published blog categories |
| GET | `/api/v1/store/blog/tags` | Public | Published blog tags |
| GET | `/api/v1/store/pickup-locations` | Public | Enabled public pickup locations |
| GET | `/api/v1/store/delivery-areas` | Public | Enabled area codes and labels |
| POST | `/api/v1/store/contact` | Public; throttled + anti-spam | Submit bounded contact enquiry to queued email; no arbitrary recipient |
| POST | `/api/v1/analytics/events` | Session-bound; consent + throttled | Ingest allowlisted browser product_view only; other funnel events are server-generated |
| GET | `/api/v1/auth/csrf` | Public | Issue CSRF bootstrap token for current origin/audience |
| POST | `/api/v1/auth/register` | Public | Create customer identity; send verification |
| POST | `/api/v1/auth/email/verify` | Challenge | Consume verification token |
| POST | `/api/v1/auth/email/resend` | Public | Rate-limited generic verification resend |
| POST | `/api/v1/auth/login` | Public | Password login for customer audience |
| POST | `/api/v1/auth/otp/request` | Public | Generic email OTP request |
| POST | `/api/v1/auth/otp/verify` | Challenge | Consume challenge; create verified customer identity if needed |
| GET | `/api/v1/auth/google/start` | Public | OAuth redirect with state/nonce |
| GET | `/api/v1/auth/google/callback` | OAuth state | Verified callback and session establishment |
| POST | `/api/v1/auth/password/forgot` | Public | Generic password reset request |
| POST | `/api/v1/auth/password/reset` | Challenge | Reset and revoke sessions |
| POST | `/api/v1/auth/logout` | Customer session | Revoke current session |
| GET | `/api/v1/auth/session` | Customer session | Current customer identity |
| POST | `/api/v1/auth/password/change` | Customer + reauth | Change password and revoke other sessions |
| POST | `/api/v1/auth/email/change` | Customer + reauth | Request new email verification |
| POST | `/api/v1/auth/email/change/confirm` | Customer + challenge | Confirm ownership and change email |
| GET | `/api/v1/auth/sessions` | Customer session | List own sessions |
| DELETE | `/api/v1/auth/sessions/{id}` | Customer owner | Revoke own session |
| POST | `/api/v1/guest/order-access/request` | Public; throttled | Generic send order email access link |
| POST | `/api/v1/guest/order-access/verify` | Challenge | Exchange link for expiring order-scoped access |
| GET | `/api/v1/account/profile` | Customer owner | Own profile |
| PATCH | `/api/v1/account/profile` | Customer owner | Own non-authentication profile fields |
| GET | `/api/v1/account/addresses` | Customer owner | Own addresses |
| POST | `/api/v1/account/addresses` | Customer owner | Create own address |
| PATCH | `/api/v1/account/addresses/{id}` | Customer owner | Update own address |
| DELETE | `/api/v1/account/addresses/{id}` | Customer owner | Delete saved address; snapshots unaffected |
| GET | `/api/v1/account/orders` | Customer owner | Own orders |
| GET | `/api/v1/account/wishlist` | Customer owner | Own wishlist |
| POST | `/api/v1/account/wishlist/items` | Customer owner | Add product |
| DELETE | `/api/v1/account/wishlist/items/{id}` | Customer owner | Remove own wishlist item |
| GET | `/api/v1/account/reviews` | Customer owner | Own review history |
| POST | `/api/v1/account/reviews` | Customer owner | Submit verified-purchase review |
| PATCH | `/api/v1/account/reviews/{id}` | Customer owner | Edit own review and requeue moderation |
| DELETE | `/api/v1/account/reviews/{id}` | Customer owner | Withdraw own review |
| POST | `/api/v1/account/orders/claim` | Customer owner | Claim verified guest orders with matching owned email |
| GET | `/api/v1/orders/{id}` | Customer owner OR verified guest order scope | Own/order-scoped order detail |
| GET | `/api/v1/orders/{id}/tracking` | Customer owner OR verified guest order scope | Sanitized order timeline |
| GET | `/api/v1/orders/{id}/invoice` | Customer owner OR verified guest order scope | Private invoice download |
| GET | `/api/v1/orders/{id}/refunds` | Customer owner OR verified guest order scope | Own refund history |
| POST | `/api/v1/cart` | Customer owner OR opaque cart/order scope | Get/create own cart |
| GET | `/api/v1/cart` | Customer owner OR opaque cart/order scope | Read own cart |
| POST | `/api/v1/cart/items` | Customer owner OR opaque cart/order scope | Add variant/quantity |
| PATCH | `/api/v1/cart/items/{id}` | Customer owner OR opaque cart/order scope | Set own item quantity |
| DELETE | `/api/v1/cart/items/{id}` | Customer owner OR opaque cart/order scope | Remove item |
| POST | `/api/v1/cart/bundles` | Customer owner OR opaque cart/order scope | Add explicit configured component bundle |
| POST | `/api/v1/cart/coupon` | Customer owner OR opaque cart/order scope | Apply one coupon and quote eligibility |
| DELETE | `/api/v1/cart/coupon` | Customer owner OR opaque cart/order scope | Remove coupon |
| POST | `/api/v1/checkout/quote` | Customer owner OR opaque cart/order scope | Calculate authoritative expiring quote and eligible methods |
| POST | `/api/v1/checkout/orders` | Customer owner OR opaque cart/order scope | Place idempotent order from quote; reserve all stock |
| POST | `/api/v1/orders/{id}/payment-attempts` | Customer owner OR opaque cart/order scope | Initialize selected card method for owned pending order |
| GET | `/api/v1/orders/{id}/payment-attempts/{attempt_id}` | Customer owner OR opaque cart/order scope | Read sanitized payment state |
| GET | `/api/v1/admin-auth/csrf` | Public | Admin-origin CSRF bootstrap |
| POST | `/api/v1/admin-auth/login` | Public; throttled | Validate staff password; MFA challenge, not full session |
| POST | `/api/v1/admin-auth/mfa/verify` | Staff login challenge | Verify TOTP/recovery code and create staff session |
| POST | `/api/v1/admin-auth/invitations/accept` | Invitation token | Set password and start mandatory MFA enrollment |
| POST | `/api/v1/admin-auth/mfa/enroll` | Enrollment challenge OR staff reauth | Enroll TOTP; activate after verification |
| POST | `/api/v1/admin-auth/mfa/recovery-codes` | Staff reauth + MFA | Rotate recovery codes |
| POST | `/api/v1/admin-auth/reauthenticate` | Staff session + MFA | Issue short-lived sensitive-action authorization |
| POST | `/api/v1/admin-auth/password/forgot` | Public; throttled | Generic staff reset request |
| POST | `/api/v1/admin-auth/password/reset` | Staff reset challenge | Reset password; MFA still required |
| GET | `/api/v1/admin-auth/session` | Staff session | Own roles/capabilities |
| GET | `/api/v1/admin-auth/sessions` | Staff session | Own active sessions |
| DELETE | `/api/v1/admin-auth/sessions/{id}` | Staff owner | Revoke own session |
| POST | `/api/v1/admin-auth/logout` | Staff session | Revoke current session |
| GET | `/api/v1/admin/products` | catalog.view | Paginated list/filter |
| POST | `/api/v1/admin/products` | catalog.manage | Create validated draft/resource |
| GET | `/api/v1/admin/products/{id}` | catalog.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/products/{id}` | catalog.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/products/{id}` | catalog.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/categories` | catalog.view | Paginated list/filter |
| POST | `/api/v1/admin/categories` | catalog.manage | Create validated draft/resource |
| GET | `/api/v1/admin/categories/{id}` | catalog.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/categories/{id}` | catalog.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/categories/{id}` | catalog.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/brands` | catalog.view | Paginated list/filter |
| POST | `/api/v1/admin/brands` | catalog.manage | Create validated draft/resource |
| GET | `/api/v1/admin/brands/{id}` | catalog.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/brands/{id}` | catalog.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/brands/{id}` | catalog.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/tags` | catalog.view | Paginated list/filter |
| POST | `/api/v1/admin/tags` | catalog.manage | Create validated draft/resource |
| GET | `/api/v1/admin/tags/{id}` | catalog.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/tags/{id}` | catalog.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/tags/{id}` | catalog.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/collections` | catalog.view | Paginated list/filter |
| POST | `/api/v1/admin/collections` | catalog.manage | Create validated draft/resource |
| GET | `/api/v1/admin/collections/{id}` | catalog.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/collections/{id}` | catalog.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/collections/{id}` | catalog.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/attributes` | catalog.view | Paginated list/filter |
| POST | `/api/v1/admin/attributes` | catalog.manage | Create validated draft/resource |
| GET | `/api/v1/admin/attributes/{id}` | catalog.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/attributes/{id}` | catalog.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/attributes/{id}` | catalog.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/attribute-sets` | catalog.view | Paginated list/filter |
| POST | `/api/v1/admin/attribute-sets` | catalog.manage | Create validated draft/resource |
| GET | `/api/v1/admin/attribute-sets/{id}` | catalog.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/attribute-sets/{id}` | catalog.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/attribute-sets/{id}` | catalog.manage | Archive if referenced; delete only safe unused drafts |
| POST | `/api/v1/admin/products/{id}/publish` | catalog.publish | Validate required translations and publish |
| POST | `/api/v1/admin/products/{id}/unpublish` | catalog.publish | Remove from published catalog without deleting history |
| POST | `/api/v1/admin/categories/{id}/publish` | catalog.publish | Validate required translations and publish |
| POST | `/api/v1/admin/categories/{id}/unpublish` | catalog.publish | Remove from published catalog without deleting history |
| POST | `/api/v1/admin/brands/{id}/publish` | catalog.publish | Validate required translations and publish |
| POST | `/api/v1/admin/brands/{id}/unpublish` | catalog.publish | Remove from published catalog without deleting history |
| POST | `/api/v1/admin/collections/{id}/publish` | catalog.publish | Validate required translations and publish |
| POST | `/api/v1/admin/collections/{id}/unpublish` | catalog.publish | Remove from published catalog without deleting history |
| GET | `/api/v1/admin/products/{id}/variants` | catalog.view | List active/archived variants |
| POST | `/api/v1/admin/products/{id}/variants` | catalog.manage | Create a validated combination |
| POST | `/api/v1/admin/products/{id}/variant-preview` | catalog.manage | Preview bounded combinations without writes |
| POST | `/api/v1/admin/products/{id}/generate-variants` | catalog.manage | Create selected combinations; preserve existing IDs |
| PATCH | `/api/v1/admin/variants/{id}` | catalog.manage | Edit variant data; cost fields additionally require catalog.cost |
| POST | `/api/v1/admin/variants/{id}/archive` | catalog.manage | Archive variant; never remove order history |
| GET | `/api/v1/admin/variants/{id}/cost` | catalog.cost | Private cost value |
| PATCH | `/api/v1/admin/variants/{id}/cost` | catalog.cost | Audited cost update |
| PUT | `/api/v1/admin/products/{id}/attribute-values` | catalog.manage | Replace validated descriptive attribute values |
| PUT | `/api/v1/admin/products/{id}/variant-axes` | catalog.manage | Set axes/options; reject destructive referenced combinations |
| PUT | `/api/v1/admin/products/{id}/relations` | catalog.manage | Related/cross-sell/upsell links |
| PUT | `/api/v1/admin/products/{id}/images` | catalog.manage | Order/attach approved media |
| GET | `/api/v1/admin/attributes/{id}/options` | catalog.view | List controlled options |
| POST | `/api/v1/admin/attributes/{id}/options` | catalog.manage | Create translated option |
| PATCH | `/api/v1/admin/attribute-options/{id}` | catalog.manage | Edit option labels/code under reference guards |
| DELETE | `/api/v1/admin/attribute-options/{id}` | catalog.manage | Archive option or delete unused |
| PUT | `/api/v1/admin/attribute-sets/{id}/members` | catalog.manage | Set required/default attribute definitions |
| PUT | `/api/v1/admin/categories/{id}/attribute-sets` | catalog.manage | Assign reusable definitions |
| PUT | `/api/v1/admin/products/{id}/attribute-sets` | catalog.manage | Explicit product definition sets |
| PUT | `/api/v1/admin/collections/{id}/products` | catalog.manage | Manage manual collection membership |
| POST | `/api/v1/admin/media/uploads` | media.manage | Allocate bounded upload |
| POST | `/api/v1/admin/media/uploads/{id}/complete` | media.manage | Verify scan/type/hash and activate asset |
| GET | `/api/v1/admin/media` | media.manage | List public media library |
| GET | `/api/v1/admin/media/{id}` | media.manage | Asset metadata |
| DELETE | `/api/v1/admin/media/{id}` | media.manage | Delete unreferenced asset or archive reference |
| GET | `/api/v1/admin/inventory` | inventory.view | Balances, available/reserved/committed and low-stock filters |
| GET | `/api/v1/admin/inventory/movements` | inventory.view | Immutable ledger history |
| POST | `/api/v1/admin/inventory/adjustments` | inventory.adjust | Idempotent signed on-hand adjustment with reason |
| POST | `/api/v1/admin/orders/{id}/restocks` | inventory.adjust | Explicit received departed goods; bounded quantities; no refund effect |
| GET | `/api/v1/admin/orders/{id}/restocks` | inventory.view | Restock history |
| GET | `/api/v1/admin/orders` | orders.view | Order list and filters |
| GET | `/api/v1/admin/orders/{id}` | orders.view | Order detail/snapshots |
| GET | `/api/v1/admin/orders/{id}/history` | orders.view | Lifecycle, fulfillment and note history |
| POST | `/api/v1/admin/orders/{id}/transition` | orders.transition | Guarded lifecycle/fulfillment action; unpaid override additionally requires orders.complete_unpaid |
| POST | `/api/v1/admin/orders/{id}/cancel` | orders.cancel | Guarded cancellation and release of holds/commitments |
| POST | `/api/v1/admin/orders/{id}/notes` | orders.notes | Append internal note |
| GET | `/api/v1/admin/orders/{id}/invoice` | documents.view | Private invoice |
| GET | `/api/v1/admin/orders/{id}/refund-documents/{refund_id}` | documents.view | Private refund document |
| GET | `/api/v1/admin/orders/{id}/payments` | payments.view | Payment ledger and exception summaries |
| GET | `/api/v1/admin/orders/{id}/refunds` | payments.view | Refund requests/history |
| POST | `/api/v1/admin/orders/{id}/cod-collection` | payments.collect | Confirm actual cash receipt; idempotent |
| POST | `/api/v1/admin/orders/{id}/bank-verification` | payments.verify_bank | Confirm bank receipt with reference; idempotent |
| POST | `/api/v1/admin/orders/{id}/refunds` | payments.refund | Allocate full/partial refund, reserve headroom and initiate |
| POST | `/api/v1/admin/refunds/{id}/confirm-external` | payments.refund | Confirm actual external/offline refund with evidence reference |
| POST | `/api/v1/admin/payment-attempts/{id}/reconcile` | payments.reconcile | Queue provider lookup |
| POST | `/api/v1/admin/refunds/{id}/reconcile` | payments.reconcile | Queue refund lookup |
| POST | `/api/v1/admin/payment-exceptions/{id}/resolve` | payments.reconcile | Audited resolution command; cannot fabricate provider capture |
| GET | `/api/v1/admin/payment-exceptions` | payments.reconcile | Unknown/duplicate/late-capture exceptions |
| GET | `/api/v1/admin/order-status-labels` | orders.view | Paginated list/filter |
| POST | `/api/v1/admin/order-status-labels` | settings.manage | Create validated draft/resource |
| GET | `/api/v1/admin/order-status-labels/{id}` | orders.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/order-status-labels/{id}` | settings.manage | Version-checked update; no state/financial side effects |
| GET | `/api/v1/admin/customers` | customers.view | Customer list with bounded PII |
| GET | `/api/v1/admin/customers/{id}` | customers.view | Customer support profile/orders |
| PATCH | `/api/v1/admin/customers/{id}` | customers.manage | Support fields/status only; never auth credentials |
| POST | `/api/v1/admin/customers/exports` | customers.export | Queue private audited export |
| GET | `/api/v1/admin/exports/{id}` | customers.export | Export job state |
| GET | `/api/v1/admin/exports/{id}/download` | customers.export | Expiring private download |
| GET | `/api/v1/admin/reviews` | reviews.moderate | Moderation queue |
| POST | `/api/v1/admin/reviews/{id}/moderate` | reviews.moderate | Approve/reject with reason |
| GET | `/api/v1/admin/promotions` | promotions.view | Paginated list/filter |
| POST | `/api/v1/admin/promotions` | promotions.manage | Create validated draft/resource |
| GET | `/api/v1/admin/promotions/{id}` | promotions.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/promotions/{id}` | promotions.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/promotions/{id}` | promotions.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/coupons` | promotions.view | Paginated list/filter |
| POST | `/api/v1/admin/coupons` | promotions.manage | Create validated draft/resource |
| GET | `/api/v1/admin/coupons/{id}` | promotions.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/coupons/{id}` | promotions.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/coupons/{id}` | promotions.manage | Archive if referenced; delete only safe unused drafts |
| POST | `/api/v1/admin/promotions/{id}/preview` | promotions.manage | Show eligibility/conflicts/calculation against sample cart |
| POST | `/api/v1/admin/promotions/{id}/publish` | promotions.manage | Validate typed rules/schedule and publish |
| POST | `/api/v1/admin/promotions/{id}/unpublish` | promotions.manage | Disable future eligibility |
| GET | `/api/v1/admin/promotions/{id}/redemptions` | promotions.manage | Usage and reserved/committed counts |
| GET | `/api/v1/admin/delivery-zones` | delivery.view | Paginated list/filter |
| POST | `/api/v1/admin/delivery-zones` | delivery.manage | Create validated draft/resource |
| GET | `/api/v1/admin/delivery-zones/{id}` | delivery.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/delivery-zones/{id}` | delivery.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/delivery-zones/{id}` | delivery.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/delivery-areas` | delivery.view | Paginated list/filter |
| POST | `/api/v1/admin/delivery-areas` | delivery.manage | Create validated draft/resource |
| GET | `/api/v1/admin/delivery-areas/{id}` | delivery.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/delivery-areas/{id}` | delivery.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/delivery-areas/{id}` | delivery.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/delivery-methods` | delivery.view | Paginated list/filter |
| POST | `/api/v1/admin/delivery-methods` | delivery.manage | Create validated draft/resource |
| GET | `/api/v1/admin/delivery-methods/{id}` | delivery.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/delivery-methods/{id}` | delivery.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/delivery-methods/{id}` | delivery.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/delivery-rules` | delivery.view | Paginated list/filter |
| POST | `/api/v1/admin/delivery-rules` | delivery.manage | Create validated draft/resource |
| GET | `/api/v1/admin/delivery-rules/{id}` | delivery.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/delivery-rules/{id}` | delivery.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/delivery-rules/{id}` | delivery.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/pickup-locations` | delivery.view | Paginated list/filter |
| POST | `/api/v1/admin/pickup-locations` | delivery.manage | Create validated draft/resource |
| GET | `/api/v1/admin/pickup-locations/{id}` | delivery.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/pickup-locations/{id}` | delivery.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/pickup-locations/{id}` | delivery.manage | Archive if referenced; delete only safe unused drafts |
| POST | `/api/v1/admin/delivery/preview` | delivery.manage | Test address/method/time/net amount against draft rules |
| POST | `/api/v1/admin/delivery/publish` | delivery.manage | Validate nonoverlap/cutoffs and atomically activate rule revision |
| GET | `/api/v1/admin/pages` | content.view | Paginated list/filter |
| POST | `/api/v1/admin/pages` | content.manage | Create validated draft/resource |
| GET | `/api/v1/admin/pages/{id}` | content.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/pages/{id}` | content.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/pages/{id}` | content.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/banners` | content.view | Paginated list/filter |
| POST | `/api/v1/admin/banners` | content.manage | Create validated draft/resource |
| GET | `/api/v1/admin/banners/{id}` | content.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/banners/{id}` | content.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/banners/{id}` | content.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/homepage-sections` | content.view | Paginated list/filter |
| POST | `/api/v1/admin/homepage-sections` | content.manage | Create validated draft/resource |
| GET | `/api/v1/admin/homepage-sections/{id}` | content.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/homepage-sections/{id}` | content.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/homepage-sections/{id}` | content.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/navigation-menus` | content.view | Paginated list/filter |
| POST | `/api/v1/admin/navigation-menus` | content.manage | Create validated draft/resource |
| GET | `/api/v1/admin/navigation-menus/{id}` | content.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/navigation-menus/{id}` | content.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/navigation-menus/{id}` | content.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/blog-posts` | content.view | Paginated list/filter |
| POST | `/api/v1/admin/blog-posts` | content.manage | Create validated draft/resource |
| GET | `/api/v1/admin/blog-posts/{id}` | content.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/blog-posts/{id}` | content.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/blog-posts/{id}` | content.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/blog-categories` | content.view | Paginated list/filter |
| POST | `/api/v1/admin/blog-categories` | content.manage | Create validated draft/resource |
| GET | `/api/v1/admin/blog-categories/{id}` | content.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/blog-categories/{id}` | content.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/blog-categories/{id}` | content.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/blog-tags` | content.view | Paginated list/filter |
| POST | `/api/v1/admin/blog-tags` | content.manage | Create validated draft/resource |
| GET | `/api/v1/admin/blog-tags/{id}` | content.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/blog-tags/{id}` | content.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/blog-tags/{id}` | content.manage | Archive if referenced; delete only safe unused drafts |
| GET | `/api/v1/admin/redirects` | content.view | Paginated list/filter |
| POST | `/api/v1/admin/redirects` | content.manage | Create validated draft/resource |
| GET | `/api/v1/admin/redirects/{id}` | content.view | Detail with allowed fields |
| PATCH | `/api/v1/admin/redirects/{id}` | content.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/redirects/{id}` | content.manage | Archive if referenced; delete only safe unused drafts |
| POST | `/api/v1/admin/pages/{id}/preview` | content.view | Authenticated localized preview; no public cache |
| POST | `/api/v1/admin/pages/{id}/publish` | content.publish | Publish/schedule validated content |
| POST | `/api/v1/admin/pages/{id}/unpublish` | content.publish | Unpublish content |
| GET | `/api/v1/admin/pages/{id}/revisions` | content.view | Revision history |
| POST | `/api/v1/admin/pages/{id}/restore` | content.publish | Restore selected revision as new revision |
| POST | `/api/v1/admin/banners/{id}/preview` | content.view | Authenticated localized preview; no public cache |
| POST | `/api/v1/admin/banners/{id}/publish` | content.publish | Publish/schedule validated content |
| POST | `/api/v1/admin/banners/{id}/unpublish` | content.publish | Unpublish content |
| GET | `/api/v1/admin/banners/{id}/revisions` | content.view | Revision history |
| POST | `/api/v1/admin/banners/{id}/restore` | content.publish | Restore selected revision as new revision |
| POST | `/api/v1/admin/blog-posts/{id}/preview` | content.view | Authenticated localized preview; no public cache |
| POST | `/api/v1/admin/blog-posts/{id}/publish` | content.publish | Publish/schedule validated content |
| POST | `/api/v1/admin/blog-posts/{id}/unpublish` | content.publish | Unpublish content |
| GET | `/api/v1/admin/blog-posts/{id}/revisions` | content.view | Revision history |
| POST | `/api/v1/admin/blog-posts/{id}/restore` | content.publish | Restore selected revision as new revision |
| PUT | `/api/v1/admin/homepage-sections/order` | content.manage | Reorder typed sections |
| POST | `/api/v1/admin/homepage/preview` | content.view | Preview complete draft homepage/locale/time |
| POST | `/api/v1/admin/homepage/publish` | content.publish | Atomically publish section revision |
| PUT | `/api/v1/admin/navigation-menus/{id}/items` | content.manage | Replace validated menu tree |
| POST | `/api/v1/admin/navigation-menus/{id}/publish` | content.publish | Publish menu revision |
| GET | `/api/v1/admin/settings/{group}` | settings.view | Allowed groups business/theme/website/commerce/seo/localization; sanitized nonsecret data |
| PATCH | `/api/v1/admin/settings/{group}` | settings.manage | Validated draft update; currency lock enforced |
| POST | `/api/v1/admin/settings/preview` | settings.view | Draft public projection |
| POST | `/api/v1/admin/settings/publish` | settings.manage | Publish validated revision and invalidate cache |
| GET | `/api/v1/admin/settings/revisions` | settings.view | Redacted revisions |
| POST | `/api/v1/admin/settings/restore` | settings.manage | Restore safe settings as new revision; no currency/history reversal |
| GET | `/api/v1/admin/integrations` | integrations.manage | Public options and configured-secret presence only |
| PATCH | `/api/v1/admin/integrations/{code}` | integrations.manage | Write public options/secret handles; never return secrets |
| POST | `/api/v1/admin/integrations/{code}/validate` | integrations.manage | Queue safe configuration readiness check |
| GET | `/api/v1/admin/imports/template` | imports.manage | Download exact CSV header/version contract |
| POST | `/api/v1/admin/imports` | imports.manage | Upload private CSV and choose mode/mapping |
| GET | `/api/v1/admin/imports` | imports.manage | Import job history |
| GET | `/api/v1/admin/imports/{id}` | imports.manage | Progress and summary |
| POST | `/api/v1/admin/imports/{id}/validate` | imports.manage | Full-file validation and staged dependencies |
| POST | `/api/v1/admin/imports/{id}/dry-run` | imports.manage | Produce immutable preview plan/hash without domain writes |
| GET | `/api/v1/admin/imports/{id}/preview` | imports.manage | Paginated row and object changes |
| GET | `/api/v1/admin/imports/{id}/errors` | imports.manage | Validation error records |
| GET | `/api/v1/admin/imports/{id}/errors/download` | imports.manage | Spreadsheet-safe CSV error report |
| POST | `/api/v1/admin/imports/{id}/confirm` | imports.manage | Idempotent whole-file commit with plan hash; cost/stock permissions also enforced |
| POST | `/api/v1/admin/imports/{id}/cancel` | imports.manage | Cancel before commit; never undo already committed records |
| GET | `/api/v1/admin/staff` | staff.manage | Staff list |
| POST | `/api/v1/admin/staff/invitations` | staff.manage | Invite selected roles |
| DELETE | `/api/v1/admin/staff/invitations/{id}` | staff.manage | Revoke pending invitation |
| PATCH | `/api/v1/admin/staff/{id}` | staff.manage | Suspend/update support fields; guard last Super Admin |
| PUT | `/api/v1/admin/staff/{id}/roles` | staff.manage | Assign roles within actor grant scope |
| POST | `/api/v1/admin/staff/{id}/revoke-sessions` | staff.manage | Revoke staff sessions |
| GET | `/api/v1/admin/permissions` | roles.manage | Read supported capability catalog |
| GET | `/api/v1/admin/roles` | roles.manage | Paginated list/filter |
| POST | `/api/v1/admin/roles` | roles.manage | Create validated draft/resource |
| GET | `/api/v1/admin/roles/{id}` | roles.manage | Detail with allowed fields |
| PATCH | `/api/v1/admin/roles/{id}` | roles.manage | Version-checked update; no state/financial side effects |
| DELETE | `/api/v1/admin/roles/{id}` | roles.manage | Archive if referenced; delete only safe unused drafts |
| PUT | `/api/v1/admin/roles/{id}/permissions` | roles.manage | Set grants; guard privilege escalation/last admin |
| GET | `/api/v1/admin/analytics/summary` | dashboard.view | Defined sales/orders/revenue/customers and coverage |
| GET | `/api/v1/admin/analytics/sales-by-date` | dashboard.view | Date buckets |
| GET | `/api/v1/admin/analytics/sales-by-category` | dashboard.view | Primary category or ancestor rollup |
| GET | `/api/v1/admin/analytics/sales-by-brand` | dashboard.view | Snapshot brand groups |
| GET | `/api/v1/admin/analytics/best-sellers` | dashboard.view | Net accepted quantities |
| GET | `/api/v1/admin/analytics/low-stock` | dashboard.view | Current low/out-of-stock variants |
| GET | `/api/v1/admin/analytics/conversion` | dashboard.view | Session cohort formula, coverage, maturity and event counts |
| GET | `/api/v1/admin/notification-templates` | notifications.manage | Localized template list |
| PATCH | `/api/v1/admin/notification-templates/{id}` | notifications.manage | Edit restricted placeholders and sanitized content |
| POST | `/api/v1/admin/notification-templates/{id}/preview` | notifications.manage | Render with synthetic values; do not send email |
| GET | `/api/v1/admin/notifications` | operations.manage | Redacted delivery history |
| POST | `/api/v1/admin/notifications/{id}/retry` | operations.manage | Retry existing authorized recipient only |
| GET | `/api/v1/admin/audit` | audit.view | Immutable redacted audit history |
| GET | `/api/v1/admin/jobs` | operations.manage | Background/outbox/import job status |
| POST | `/api/v1/admin/jobs/{id}/retry` | operations.manage | Retry allowlisted idempotent job; never arbitrary task execution |
| POST | `/api/v1/webhooks/payments/{provider_code}` | Verified provider signature | Receive only registered adapter callbacks; dedupe/reconcile |
| GET | `/api/v1/health/live` | Infrastructure | Process liveness; no internals |
| GET | `/api/v1/health/ready` | Private infrastructure | Dependency readiness; not publicly exposed |

**Critical payload/result contracts**

| Command | Required input | Result |
|---|---|---|
| POST checkout/quote | cart_version, shipping area/address or pickup_location, method, contact, locale | quote_id, hash, expires_at (10 min), eligible methods, item/discount/delivery/zero-tax totals, reasons |
| POST checkout/orders | quote_id/hash, cart_version, payment_method_id, contact, billing/shipping data, policy acceptance; Idempotency-Key | order_id, order access scope, pending/processing, total/currency; never raw credentials |
| POST payment-attempts | order version, enabled method ID; Idempotency-Key | attempt_id, normalized status, hosted redirect URL/expiry |
| POST refunds | item allocation amounts/quantities, optional delivery refund, reason, full/partial mode, currency; Idempotency-Key | refund_id, held amount, normalized status; no stock mutation |
| POST restocks | order_item IDs and integer quantities, received_goods reason; Idempotency-Key | movement IDs and available stock; no refund mutation |
| POST import confirm | plan_hash, file_hash, mapping/version, preview_revision, selected mode/stock_mode; Idempotency-Key | job_id and 202, or 409 stale; result committed/rejected all-or-none |
| POST transition | expected_version, approved action, reason, optional unpaid override | new internal/display state plus timeline ID |
| POST analytics/events | product_view event_id/session/page_view/product, locale, occurrence time | accepted/duplicate/rejected; cannot submit purchase events |

**Public/customer validation:** the combined cart/order-scope label means a cart cookie authorizes only its own cart and checkout. After placement an order-specific opaque scope is issued for that order; it is not permission to enumerate arbitrary orders. Account/session endpoints never accept arbitrary customer IDs. Guest email-access links are required for later tracking/private invoice access.

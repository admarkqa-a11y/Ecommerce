# Frontend implementation status — 0.4.1

Updated 6 October 2026. The marketplace storefront update is described in MARKETPLACE_UPDATE.md and verified in VERIFICATION_0.4.1.md. All remaining production limitations below still apply.

Original integration context, 5 October 2026. The owner authorized frontend work after backend 0.3. This release includes both Next.js applications and the backend source they integrate with.

## Customer storefront

Implemented: configurable store identity/colors/logo/contact/currency; English/Arabic routes and RTL; server-rendered public homepage/product/page content; published predefined homepage sections in configured order; category/brand/search/stock/sort filters and paged catalog; variant selection and stock availability; cart quantity/removal/coupons; explicit bundles; authoritative delivery quotes with quote expiry; COD/bank/card choices based on configuration; hosted card-payment handoff; customer password/OTP login and registration; password reset/change; owned saved addresses; order history/invoices; wishlist removal; comparison by stored product codes; published reviews and verified-purchase review submission; WhatsApp click-to-chat; optional analytics consent and product-view events.

Checkout does not collect card data or mark a redirect as payment success. Payment status comes from the backend. Failed or exceptional payment outcomes do not display a success confirmation. Optional analytics can be declined without blocking shopping.

## Admin application

Implemented: password + TOTP sign-in, permission-aware navigation/actions and read-only catalog access; date-filtered sales/revenue/customer/stock/conversion reports with definitions; catalog/category/brand/attribute/option editing; typed descriptive attribute assignment; variant creation; explicit publishing; inventory adjustments; order transitions, collection, full/partial amount and item refunds, manual refund confirmation, separately recorded stock returns; CSV upload/validation/preview/error download/dry run/confirmation/history; delivery and promotion resource editing, including product/category/brand scopes; content and scheduled homepage-section editing; white-label settings; role capability editing; uncertain card-payment reconciliation; notification retries.

Financial/stock command keys persist across retries while the editor remains open. Backend permissions and transaction rules remain authoritative. Advanced JSON fields are exposed for rule/property configuration and are not a complete guided promotion/variant wizard. Most main navigation, reports and customer messages are bilingual; some advanced model choices, status codes and server validation messages remain English and require a final Arabic copy pass.

## Remaining frontend and full-platform work

- Real-browser desktop/mobile/RTL visual QA, keyboard/screen-reader review and cross-browser acceptance are outstanding. Chromium startup was blocked by environment socket restrictions; no screenshots or browser-click pass is claimed.
- Full guided bundle/BXGY rule construction, customer-target selection, bulk variant generation, richer homepage draft preview and complete content revision workflows are not delivered. Current advanced resource forms use backend schemas/JSON for these properties.
- Facet discovery/filter widgets, full customer/staff management, media uploading/multiple product images, immutable issued PDF invoices, guest re-entry/cart merging and other missing backend capabilities remain subject to the backend status document.
- Homepage featured product IDs currently select from the loaded public catalog batch (24 products by default). Large curated selections need a dedicated product-selection API and matching picker before launch. Basic featured sections without explicit IDs use the first eight loaded products.
- Offers currently surface sale-priced products from the loaded catalog page and eligible bundles. General promotion discount previews are authoritative at checkout; the storefront does not advertise unverified pre-checkout promotion amounts.
- Live SkipCash merchant/sandbox verification, PostgreSQL locking tests, Docker/TLS deployment, image-digest isolation, media recovery and full SOW acceptance remain release gates. This release does not remove the backend 0.3 limitations.

No client-specific name, inventory, product taxonomy, contact information or merchant credentials are embedded into frontend source. Demo identity/catalog/content come from synthetic seed data; new clients get separate deployments, never copied production databases.

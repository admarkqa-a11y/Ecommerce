# Storefront marketplace update — 0.4.1

The customer storefront now implements the approved marketplace design direction. This package contains the updated storefront, existing admin application, and backend. It does not certify completion of all Version 1 production gates.

## What changed

- Runtime-branded header, prominent search on all screen sizes, account/cart shortcuts, native category menu, and category navigation sourced from the catalog.
- Search text persists in the URL and is applied during server rendering. Switching language on the shop page preserves the search and category/brand selections. Pagination and other existing filters remain available.
- Promotional hero, category tiles, compact editorial/promotion panels, and featured-product cards use the existing published homepage section order.
- Product cards use actual product/variant prices, calculated sale percentages, stock availability, wishlist, comparison, and existing add-to-cart/variant-selection actions. No fabricated ratings, sold counts, stock urgency, or delivery promises.
- English/Arabic layouts, logical CSS positioning, mobile reflow, and automatic black/white header text contrast for client colors.
- Product and hero images use configured URLs. If images are missing, the design uses neutral catalog placeholders. The gaming demo still contains its two real demo catalog records; the extra products from the design concept were not fabricated in the application.

## Existing installation

Deploy the updated storefront using your existing runtime API configuration. No schema migration is introduced by this update. Existing client business settings and published sections remain intact. The admin and commerce service interfaces are unchanged.

The storefront CSS is separate from admin styling. Build the storefront with `npm run build --workspace @retail/storefront`. Local startup and full platform deployment instructions remain in START_HERE.md and DEPLOYMENT.md.

To match the approved yellow demo, set Primary color to `#FFE600` and Accent color to `#E7E7FF` in that client's settings. This is optional and not hard-coded into client deployments. New empty development databases seeded with `seed_demo a` use these colors and sample homepage sections. Do not rerun the demo seeder against an existing client database.

## Homepage configuration

Use the current admin Content/Sections editor, order sections, and publish each edit. Suggested arrangement:

1. Hero.
2. Categories.
3. Promotion panel and compact editorial panel.
4. Featured products.

Optional section properties:

- Hero: `image_url`, `image_alt`, `image_alt_ar`. Use an HTTPS or same-origin image URL and descriptive bilingual alt text. With no image, the hero uses products from the loaded catalog or a neutral placeholder.
- Categories/brands: `icons` object keyed by category/brand code. Values refer to existing shared Icon names, for example `{"gaming":"grid","cables":"box"}`. Unrecognized names fall back to the neutral box.
- Text: `{"layout":"compact"}` places the editorial panel alongside a promotion on wider screens, with a link to the catalog. Mobile stacks these panels.
- Featured products: existing `product_ids` behavior remains limited to the loaded catalog batch, as documented in STATUS.md.

The current admin uses JSON for advanced section properties; this release does not introduce a guided visual page builder.

## Recommended next design improvements

Use consistent real product photography and one branded hero image. Put the most useful four to six categories first. Avoid adding delivery promises or countdowns until actual delivery and promotion configuration supports them. These are content recommendations, not unimplemented checkout dependencies.

## Validation and remaining gates

See VERIFICATION_0.4.1.md for checks performed in this update. Existing backend and frontend status documents remain applicable, including large catalog curation/faceting limitations and live gateway/deployment acceptance. Browser visual acceptance remains required before launch.

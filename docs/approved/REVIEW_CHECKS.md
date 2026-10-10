# Documentation consistency check

These are document/sample checks only. They are not application, database migration, gateway or production acceptance tests.

- All 16 requested deliverables are mapped in README and the specification.
- 126 declared logical entities and 187 foreign-key references resolve to declared tables/fields.
- 345 unique API method/path combinations; all named admin capabilities map to the 39-capability permission matrix.
- Database design excludes warehouse/supplier/shared-tenant/tax-rate tables for V1.
- CSV samples were authored through the spreadsheet runtime, exported as CSV, visually checked for identification columns, then parsed and validated against the documented sample definitions.
- Client A: 3 valid variant rows, 2 products, correct JSON/Arabic fields and unique SKUs/combinations.
- Client B: 3 valid variant rows, 2 products, correct JSON/Arabic fields and unique SKUs/combinations.
- Promotion arithmetic examples reconcile to their stated totals; this does not test a promotion engine.
- Markdown fences are balanced; package filenames/references are present.
- Manual consistency review covers stock reserve/commit/departure, refunds versus restock, draft/publication isolation, promotion/coupon allocation, zero tax, one currency, guest ownership, import atomicity and clone isolation.

**Not yet performed:** implementation, executable migrations, rendered DBML parser validation, browser/application testing, actual import transactions, live gateway integration, load/security/recovery tests, or two-client deployments. These remain phase gates in the specification.

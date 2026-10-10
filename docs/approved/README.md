# Version 1 architecture review package

**Documentation only — no application implementation or deployment has begun.**

Start with `RETAIL_V1_SPECIFICATION.md`. The user's latest Version 1 decisions are the baseline; all operational defaults are explicitly documented. The master remains industry-independent.

| Requested deliverable | Location |
|---|---|
| 1. Final ERD | DATABASE_ERD.md + DATABASE_SCHEMA.dbml |
| 2. Complete API endpoint list | API_ENDPOINTS.md |
| 3. Permission matrix | PERMISSION_MATRIX.md |
| 4. Module dependency map | Specification section 4 |
| 5. Final folder structure | Specification section 5 |
| 6. Deployment architecture | Specification section 6 |
| 7. Client cloning procedure | Specification section 7 |
| 8. Import format/sample CSV | IMPORT_FORMAT.md + products_client_a.csv + products_client_b.csv |
| 9. Payment adapter interface | Specification section 9 |
| 10. Order/payment/inventory states | Specification section 10 |
| 11. Promotion calculation rules | Specification section 11 |
| 12. Tax calculation rules | Specification section 12: disabled, zero amounts |
| 13. Analytics definitions | Specification section 13 |
| 14. Security checklist | Specification section 14 |
| 15. Testing strategy | Specification section 15 |
| 16. V1 scope/exclusions | Specification section 16 |

The DBML is a logical design for review, not executable SQL migrations. The API document is a complete method/path inventory with permission bindings, not a claim that endpoints exist. Mermaid diagrams render in compatible Markdown viewers. CSV files contain fictional data, are whole-file import examples, and require the prerequisite definitions in IMPORT_FORMAT.md.

**Defaults resolved without further questions**

- Tax disabled, no tax-management module in V1.
- Atomic confirmed CSV files: no partial catalog or stock import.
- Priority-first automatic offers; one coupon only on otherwise undiscounted units.
- Refunds and restocking are independent audited actions.
- Clear reserved/committed/physically departed inventory quantities.
- One order fulfillment and one transactional currency per deployment.
- First-party conversion is accepted purchases divided by qualified shopping sessions, with cohort and coverage rules documented.
- English/Arabic and RTL begin in the foundation.
- Same release images with isolated client databases, media, credentials and domains.

**Only remaining commercial selection:** the first live card gateway/approved merchant account. No provider-specific capability is assumed. Sandbox credentials and current provider documentation will be needed to implement and test that adapter. The rest of the design is ready for review without additional clarification questions.

No real credentials, client customer information, production database contents or production code are included.

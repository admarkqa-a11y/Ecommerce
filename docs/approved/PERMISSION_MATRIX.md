# Version 1 permission matrix

All staff actions require an active staff session, MFA and the listed capability. Super Admin (S) receives every capability below. Manager (M), Content Manager (C) and Order Staff (O) receive only checked grants. Customer is never an admin role. Custom roles may combine these capabilities; they cannot invent new backend actions.

| Capability | Meaning | S | M | C | O |
|---|---|:---:|:---:|:---:|:---:|
| `dashboard.view` | View aggregate dashboard and conversion | ✓ | ✓ | — | — |
| `catalog.view` | View catalog configuration | ✓ | ✓ | — | — |
| `catalog.manage` | Create/edit/archive catalog, variants and definitions | ✓ | ✓ | — | — |
| `catalog.publish` | Publish/unpublish catalog | ✓ | ✓ | — | — |
| `catalog.cost` | Read/write cost prices | ✓ | — | — | — |
| `media.manage` | Upload/manage public merchandising assets | ✓ | ✓ | ✓ | — |
| `inventory.view` | View balances/low stock/history | ✓ | ✓ | — | — |
| `inventory.adjust` | Adjust/import on-hand and explicitly restock | ✓ | ✓ | — | — |
| `orders.view` | View orders, fulfillment details and customer contact needed for orders | ✓ | ✓ | — | ✓ |
| `orders.transition` | Process/dispatch/complete permitted fulfillment transitions | ✓ | ✓ | — | ✓ |
| `orders.cancel` | Cancel eligible orders | ✓ | ✓ | — | — |
| `orders.notes` | Add internal order notes | ✓ | ✓ | — | ✓ |
| `orders.complete_unpaid` | Override unpaid COD completion with reason | ✓ | — | — | — |
| `payments.view` | View payment/refund summaries | ✓ | ✓ | — | ✓ |
| `payments.collect` | Confirm COD collection | ✓ | ✓ | — | ✓ |
| `payments.verify_bank` | Confirm received bank transfers | ✓ | ✓ | — | — |
| `payments.refund` | Initiate/confirm full or partial refunds | ✓ | — | — | — |
| `payments.reconcile` | Run payment/refund reconciliation and resolve exceptions | ✓ | — | — | — |
| `documents.view` | Download authorized order invoices/refund documents | ✓ | ✓ | — | ✓ |
| `customers.view` | View customers and addresses for support | ✓ | ✓ | — | — |
| `customers.manage` | Update customer support fields or suspend account | ✓ | ✓ | — | — |
| `customers.export` | Export customer personal data | ✓ | — | — | — |
| `reviews.moderate` | Moderate customer reviews | ✓ | ✓ | ✓ | — |
| `promotions.view` | Read promotion/coupon configuration | ✓ | ✓ | — | — |
| `promotions.manage` | Edit/preview/publish supported promotions | ✓ | ✓ | — | — |
| `content.view` | Read CMS, blog, navigation and revisions | ✓ | ✓ | ✓ | — |
| `content.manage` | Edit content and public media | ✓ | — | ✓ | — |
| `content.publish` | Publish/schedule/restore content versions | ✓ | — | ✓ | — |
| `delivery.view` | Read delivery configuration | ✓ | ✓ | — | ✓ |
| `delivery.manage` | Edit/publish delivery rules and pickup availability | ✓ | — | — | — |
| `settings.view` | Read non-secret business/website/commerce configuration | ✓ | ✓ | ✓ | — |
| `settings.manage` | Change/publish business/website/commerce configuration | ✓ | — | — | — |
| `integrations.manage` | Configure payment/email/OAuth secret references and validate readiness | ✓ | — | — | — |
| `imports.manage` | Upload/validate/preview/commit catalog CSV subject to extra field permissions | ✓ | ✓ | — | — |
| `staff.manage` | Invite/suspend staff and assign roles | ✓ | — | — | — |
| `roles.manage` | Create/edit roles from supported capability catalog | ✓ | — | — | — |
| `audit.view` | Read redacted audit records | ✓ | — | — | — |
| `operations.manage` | View/retry safe failed tasks and notification delivery | ✓ | — | — | — |
| `notifications.manage` | Edit localized email templates and preview | ✓ | — | ✓ | — |

**Additional enforcement**

- Cost price is stripped unless `catalog.cost`; an import containing a cost field requires it, even when `imports.manage` is granted. A manager may omit the entire cost column on update or use an approved file without cost changes. A new product without supplied cost stores null, never an invented zero.
- Stock replacement/restock requires `inventory.adjust`; ordinary catalog editing never directly writes inventory. Import confirmation checks the combined permissions for every field/action.
- Refund permission is separate from order management and cash collection. Super Admin grants it explicitly to a trusted custom role if desired.
- Content Manager may manage content/SEO but cannot change global business identity, currency, payment settings, legal publisher identity or credentials. Policy page editing is audited; publishing remains content.publish.
- Orders/view grants only customer data needed for that order. It does not grant customer export or unrestricted profile edits. Staff cannot retrieve passwords/OTP/MFA secrets.
- Staff role assignment cannot grant capabilities the actor does not possess; only Super Admin has staff.manage/roles.manage initially. Last active Super Admin cannot be removed.
- Public: published catalog, content, configuration allowlist, active public reviews. Guest: own opaque cart and checkout; verified order-scoped tracking/invoice access. Customer: own profile/addresses/orders/wishlist/reviews. Neither guest nor customer may choose an owner ID in a request to access another identity.
- Review submission requires a signed-in customer with a delivered/collected order item for the product; one review per customer/product, edits return to pending moderation. No unverified reviews in the V1 default.
- Generic account support updates cannot change authentication email or password. The customer email-change flow verifies old/current authentication and new email ownership.
- All refunds, restocks, bank confirmations, unpublished content previews, private downloads, exports and import commits are audited.

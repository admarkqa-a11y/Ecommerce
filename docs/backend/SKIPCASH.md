# SkipCash adapter and verification boundary

SkipCash is the selected card gateway. COD and bank transfer remain independent adapters. Card payments default to disabled.

The implementation follows the publicly indexed official legacy integration manual:
https://skipcash.app/assets/doc/SkipCashIntegrationManual.pdf
The current developer portal was unavailable during implementation. Its current merchant contract, checkout hostnames and sandbox behavior must be verified before enabling the adapter for real customers. No live or sandbox merchant request was executed here.

## Secure configuration

Set CARD_ENABLED, CARD_PROVIDER=skipcash, SKIPCASH_ENV, SKIPCASH_CLIENT_ID, SKIPCASH_KEY_ID, SKIPCASH_KEY_SECRET, SKIPCASH_WEBHOOK_KEY, SKIPCASH_CHECKOUT_HOSTS and PAYMENT_RETURN_URL through deployment secrets. Production rejects sandbox mode. Sandbox testing can use ENVIRONMENT=staging with HTTPS and PostgreSQL/Redis. Never paste credentials into source, fixtures, CSVs or shared documentation. The provider currently supports QAR only; this is a provider capability check, not hard-coded store currency.

Register HTTPS `/api/v1/payments/webhooks/skipcash` with the provider. Return URL is a customer navigation destination and cannot mark an order paid. Creation uses signed payloads and a stable attempt identifier. A verified webhook triggers authoritative provider status lookup; payment ID, merchant reference, amount and currency must match the stored order. Browser-supplied success is never accepted.

Attempts persist before network calls. Unknown results remain reserved and require reconciliation; retries do not blindly create a second charge. Confirmed failures release eligible pending orders. Late captures enter paid_exception, record the financial event and do not automatically fulfill. A stale pending notification cannot downgrade a paid order. Webhook receipts and capture operations are idempotent.

Refund execution through a provider API is not implemented because an authoritative refund endpoint contract was unavailable. Admins must execute the refund in the merchant portal, verify its provider reference and record/confirm it in the backend. A provider refund status alone does not establish a partial refund amount and is flagged for review. Money refunds never restock inventory.

## Mandatory merchant acceptance

Verify signed creation and hosted checkout, successful/failed/cancelled payment, duplicate/out-of-order webhook, invalid signature, amount/currency/reference mismatch, network timeout and unknown outcome, late capture after order expiry/cancellation, reconciliation after worker outage, portal full/partial refund and matching ledger history. Confirm actual approved checkout hostnames rather than widening the allowlist. Record sanitized evidence and current API contract version. This gate is outstanding.

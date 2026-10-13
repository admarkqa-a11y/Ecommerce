"""Provider-independent contract. No card provider is silently simulated."""
from dataclasses import dataclass,field
from decimal import Decimal
from typing import Protocol,Mapping

@dataclass(frozen=True)
class PaymentRequest:
    attempt_id: str
    amount: Decimal
    currency: str
    idempotency_key: str
    return_url: str
    contact: dict = field(default_factory=dict)

@dataclass(frozen=True)
class PaymentResult:
    reference: str
    state: str
    amount: Decimal
    currency: str
    redirect_url: str | None = None
    merchant_reference: str = ''

class ProviderUnavailable(Exception):pass
class InvalidProviderResponse(Exception):pass
class InvalidWebhook(Exception):pass

class PaymentAdapter(Protocol):
    currencies: tuple[str,...]
    supports_refund_api: bool
    def ready(self) -> bool: ...
    def create_payment(self, request: PaymentRequest) -> PaymentResult: ...
    def retrieve_payment(self, reference: str) -> PaymentResult: ...
    def verify_and_parse_webhook(self, body: bytes, headers: Mapping[str,str]) -> tuple[str,str]: ...
    def request_refund(self, reference: str, amount: Decimal, key: str) -> PaymentResult: ...
    def retrieve_refund(self, reference: str) -> PaymentResult: ...

ADAPTERS: dict[str,PaymentAdapter] = {}

def get_adapter(code: str) -> PaymentAdapter:
    if code=='skipcash':
        from .skipcash import SkipCashAdapter
        return SkipCashAdapter()
    if code not in ADAPTERS:
        raise ValueError('No verified card adapter is installed for this provider.')
    return ADAPTERS[code]

def card_enabled():
    from django.conf import settings
    from apps.configuration.models import StoreSettings
    if not settings.CARD_ENABLED:return False
    try:
        adapter=get_adapter(settings.CARD_PROVIDER)
        return adapter.ready() and StoreSettings.current().currency in adapter.currencies
    except (ValueError,ProviderUnavailable):return False

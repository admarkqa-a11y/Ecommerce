"""Durable card attempts: no network call under a database lock and no blind POST retry."""
import hashlib
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from common.api import Conflict
from apps.orders.models import Order, History
from .models import PaymentAttempt, WebhookReceipt, Capture
from .adapters import get_adapter,PaymentRequest,ProviderUnavailable,InvalidProviderResponse

def start(order_id):
    with transaction.atomic():
        order=Order.objects.select_for_update().get(pk=order_id)
        if order.payment_method!='card':raise ValidationError('This order does not use card payment.')
        attempt=PaymentAttempt.objects.select_for_update().get(order=order)
        if attempt.state!='created':return attempt
        if order.state!='pending':raise Conflict('Order is no longer pending.')
        attempt.state='creating';attempt.save()
        request=PaymentRequest(str(attempt.id),order.total,order.currency,str(attempt.id),settings.PAYMENT_RETURN_URL,order.contact)
    try:
        result=get_adapter(attempt.provider).create_payment(request)
        return apply_result(attempt.id,result)
    except (ProviderUnavailable,InvalidProviderResponse):
        PaymentAttempt.objects.filter(pk=attempt.id,state='creating').update(state='unknown',issue='create_outcome_unknown')
        attempt.refresh_from_db();return attempt

@transaction.atomic
def apply_result(attempt_id,result):
    # Same lock order as payment collection/cancellation: order, attempt, promotions, stock.
    initial=PaymentAttempt.objects.get(pk=attempt_id)
    order=Order.objects.select_for_update().get(pk=initial.order_id)
    attempt=PaymentAttempt.objects.select_for_update().get(pk=attempt_id)
    if (result.amount!=order.total or result.currency!=order.currency or result.merchant_reference!=str(attempt.id)
        or (attempt.reference and attempt.reference!=result.reference)):
        attempt.issue='amount_currency_or_reference_mismatch';attempt.save()
        return attempt
    attempt.reference=result.reference;attempt.last_checked_at=timezone.now()
    if result.redirect_url:attempt.checkout_url=result.redirect_url
    if result.state=='paid':
        if order.state=='cancelled':
            Capture.objects.get_or_create(operation_key=f'card:{attempt.provider}:{result.reference}',defaults={
                'order':order,'reference':result.reference,'amount':order.total})
            order.payment_state='paid_exception';order.save()
            attempt.state='paid';attempt.issue='late_capture_requires_refund_review'
        else:
            from .services import record_capture
            record_capture(order.id,result.reference,f'card:{attempt.provider}:{result.reference}',None,verified_card=True)
            attempt.state='paid';attempt.issue=''
    elif result.state=='failed' and attempt.state!='paid':
        attempt.state='failed';attempt.issue='';attempt.save()
        from apps.orders.services import transition
        if order.state=='pending':transition(order.id,'cancel',reason='Provider verified failed payment',payment_resolved=True)
    elif result.state=='external_refund':
        attempt.issue='external_refund_requires_ledger_review'
    elif attempt.state not in ['paid','failed']:
        attempt.state=result.state;attempt.issue=''
    attempt.save()
    return attempt

def reconcile(attempt_id,reference=None):
    attempt=PaymentAttempt.objects.get(pk=attempt_id)
    selected=reference or attempt.reference
    if not selected:
        PaymentAttempt.objects.filter(pk=attempt.id,state='creating').update(state='unknown',issue='missing_provider_reference')
        raise Conflict('Provider reference required to reconcile unknown creation outcome. Do not retry payment creation.')
    result=get_adapter(attempt.provider).retrieve_payment(selected)
    return apply_result(attempt.id,result)

def webhook(provider,body,headers):
    adapter=get_adapter(provider)
    reference,attempt_id=adapter.verify_and_parse_webhook(body,headers)
    attempt=PaymentAttempt.objects.get(pk=attempt_id,provider=provider)
    receipt,_=WebhookReceipt.objects.get_or_create(digest=hashlib.sha256(body).hexdigest(),defaults={'attempt':attempt})
    if receipt.processed_at:return attempt
    attempt=reconcile(attempt.id,reference)
    if attempt.issue=='amount_currency_or_reference_mismatch':raise InvalidProviderResponse('Gateway reconciliation mismatch.')
    receipt.processed_at=timezone.now();receipt.save()
    return attempt

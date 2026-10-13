from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError
from common.api import Conflict
from common.money import money
from apps.orders.models import Order,History
from apps.orders.services import accept
from .models import Capture,Refund
from django.utils import timezone
from common.validation import whole_units
from common.money import allocate

@transaction.atomic
def request_item_refund(order_id,selections,delivery,reason,key,actor):
    order=Order.objects.select_for_update().get(pk=order_id)
    if not isinstance(selections,list):raise ValidationError('items must be a list.')
    delivery=money(delivery or 0,order.exponent)
    request={'items':selections,'delivery':str(delivery)}
    prior=Refund.objects.filter(operation_key=key).first()
    if prior:
        if prior.order_id!=order.id or prior.allocations.get('request')!=request:raise Conflict('Key reused for a different item refund.')
        return prior
    existing=list(order.refunds.filter(state__in=['pending','succeeded','unknown']))
    delivery_used=sum((Decimal(r.allocations.get('delivery','0')) for r in existing),Decimal(0))
    if delivery+delivery_used>order.delivery_fee:raise ValidationError('Delivery refund exceeds the original delivery fee.')
    allocation={};amount=delivery
    for selection in selections:
        if not isinstance(selection,dict):raise ValidationError('Each refund item must be an object.')
        from django.shortcuts import get_object_or_404
        item=get_object_or_404(order.items,pk=selection.get('order_item_id'))
        key_id=str(item.id)
        if key_id in allocation:raise ValidationError('Duplicate refund item.')
        quantity=whole_units(selection.get('quantity'),minimum=1)
        used={index for r in existing for index in r.allocations.get('items',{}).get(key_id,[])}
        available=[i for i in range(item.quantity) if i not in used]
        if len(available)<quantity:raise ValidationError('Refund quantity exceeds remaining units.')
        chosen=available[:quantity]
        unit_net=item.snapshot.get('unit_net') or [str(v) for v in allocate(item.net,[1]*item.quantity,order.exponent)]
        amount+=sum((Decimal(unit_net[i]) for i in chosen),Decimal(0));allocation[key_id]=chosen
    refund=request_refund(order.id,amount,reason,key,actor)
    refund.allocations={'items':allocation,'delivery':str(delivery),'request':request};refund.save()
    return refund

@transaction.atomic
def record_capture(order_id,reference,key,actor,*,verified_card=False):
    if not isinstance(reference,str) or not 1<=len(reference.strip())<=200 or not isinstance(key,str) or not 1<=len(key)<=250:raise ValidationError('A reference (up to 200 characters) and idempotency key (up to 250 characters) are required.')
    order=Order.objects.select_for_update().get(pk=order_id)
    if order.payment_method=='card' and not verified_card:raise ValidationError('Card capture requires verified provider reconciliation.')
    prior=Capture.objects.filter(operation_key=key).first()
    if prior:
        if prior.order_id!=order.id or prior.reference!=reference:raise Conflict('Key already used for another collection.')
        return prior
    if order.state=='cancelled':raise ValidationError('Cancelled order: reconcile late payment separately.')
    if order.captures.exists():raise ValidationError('Payment already collected.')
    capture=Capture.objects.create(order=order,amount=order.total,reference=reference,operation_key=key,actor=actor)
    order.payment_state='paid';order.save();accept(order)
    History.objects.create(order=order,action='payment_received',actor=actor,reason=reference)
    return capture

@transaction.atomic
def request_refund(order_id,amount,reason,key,actor):
    order=Order.objects.select_for_update().get(pk=order_id)
    amount=money(amount,order.exponent)
    if amount<=0 or not isinstance(reason,str) or not reason.strip() or not isinstance(key,str) or not 1<=len(key)<=250:raise ValidationError('Amount, reason and idempotency key are required.')
    prior=Refund.objects.filter(operation_key=key).first()
    if prior:
        if prior.order_id!=order.id or prior.amount!=amount:raise Conflict('Key reused for a different refund.')
        return prior
    captured=order.captures.aggregate(n=Sum('amount'))['n'] or Decimal(0)
    reserved=order.refunds.filter(state__in=['pending','succeeded','unknown']).aggregate(n=Sum('amount'))['n'] or Decimal(0)
    if amount>captured-reserved:raise ValidationError('Refund exceeds remaining captured balance.')
    if amount==captured-reserved and not order.departed_at and order.state!='cancelled':raise ValidationError('Cancel unfulfilled order before a full refund.')
    refund=Refund.objects.create(order=order,amount=amount,reason=reason,operation_key=key,actor=actor)
    History.objects.create(order=order,action='refund_requested',actor=actor,reason=reason)
    return refund

@transaction.atomic
def confirm_refund(refund_id,reference,actor):
    refund=Refund.objects.select_related('order').get(pk=refund_id)
    order=Order.objects.select_for_update().get(pk=refund.order_id)
    refund=Refund.objects.select_for_update().get(pk=refund_id)
    if refund.state=='succeeded':
        if reference!=refund.reference:raise Conflict('Refund is already confirmed with a different reference.')
        return refund
    if refund.state!='pending' or not isinstance(reference,str) or not 1<=len(reference.strip())<=200:raise ValidationError('A verified external refund reference is required.')
    refund.state='succeeded';refund.reference=reference;refund.succeeded_at=timezone.now();refund.save()
    total=order.refunds.filter(state='succeeded').aggregate(n=Sum('amount'))['n'] or Decimal(0)
    order.payment_state='refunded' if total>=order.total else 'partially_refunded';order.save()
    History.objects.create(order=order,action='refund_succeeded',actor=actor,reason=reference)
    from apps.operations.models import Outbox
    Outbox.objects.get_or_create(key='refund:'+str(refund.id),defaults={'event_type':'refund.succeeded','payload':{'order_id':str(order.id),'refund_id':str(refund.id)}})
    return refund

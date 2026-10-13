import hashlib,json
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError,PermissionDenied
from common.api import Conflict
from common.money import money
from apps.catalog.services import published_variant
from apps.configuration.models import StoreSettings
from apps.inventory.models import Balance
from apps.inventory.services import move
from apps.promotions.models import Promotion,Redemption
from apps.promotions.services import calculate
from apps.delivery.services import quote_delivery
from apps.analytics.models import Event
from apps.operations.models import Outbox
from .models import Cart,Quote,Order,OrderItem,History

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,default=str,separators=(',',':')).encode()).hexdigest()

def get_cart(request):
    from apps.analytics.services import shopping_session
    attribution=shopping_session(request)
    def bind(cart):
        if cart.shopping_session_id!=getattr(attribution,'id',None):
            cart.shopping_session=attribution;cart.save(update_fields=['shopping_session'])
        return cart
    if not request.session.session_key:request.session.create()
    if request.user.is_authenticated:
        cart=Cart.objects.filter(owner=request.user,active=True).first()
        if cart:return bind(cart)
    cart=Cart.objects.filter(session_key=request.session.session_key,active=True).first()
    if cart:
        if request.user.is_authenticated and cart.owner_id is None:cart.owner=request.user;cart.save()
        return bind(cart)
    return bind(Cart.objects.create(session_key=request.session.session_key,owner=request.user if request.user.is_authenticated else None))

def totals(cart,method_id,area_id=None):
    settings=StoreSettings.current();lines=[]
    for item in cart.items.select_related('variant__product__category','variant__product__brand').order_by('variant_id'):
        v=item.variant;pub=published_variant(v)
        if item.quantity<1 or item.quantity>50:raise ValidationError('Quantity must be between 1 and 50.')
        if v.inventory.available<item.quantity:raise ValidationError(f'Insufficient stock: {v.sku}')
        lines.append({'variant':v,'quantity':item.quantity,'price':pub['price'],'sale_price':pub['sale_price'],'snapshot':v.product.publication})
    from apps.catalog.models import Variant
    from apps.promotions.services import customer_eligible
    for group in cart.bundles.select_related('promotion').order_by('id'):
        p=group.promotion;now=timezone.now()
        if (not p.enabled or p.kind!='bundle' or (p.starts_at and p.starts_at>now) or (p.ends_at and p.ends_at<=now)
            or not customer_eligible(p,cart.owner) or (p.global_limit is not None and p.used+p.held>=p.global_limit)):
            raise ValidationError('A selected bundle is no longer eligible.')
        p.full_clean()
        for instance in range(group.quantity):
            for variant_id,qty in sorted(p.rules['components'].items()):
                variant=Variant.objects.select_related('product__category','product__brand').get(pk=variant_id)
                pub=published_variant(variant)
                lines.append({'variant':variant,'quantity':qty,'price':pub['price'],'sale_price':pub['sale_price'],
                    'snapshot':variant.product.publication,'bundle_group':f'{group.id}:{instance}','bundle_promotion':str(p.id)})
    if not lines:raise ValidationError('Your cart is empty.')
    if sum(x['quantity'] for x in lines)>200:raise ValidationError('Maximum 200 units per order.')
    quantities={}
    for line in lines:
        key=line['variant'].id;quantities[key]=quantities.get(key,0)+line['quantity']
    for variant_id,qty in quantities.items():
        if Balance.objects.get(variant_id=variant_id).available<qty:raise ValidationError('Insufficient combined stock for cart and bundle components.')
    discounts,promo_ids,detail=calculate(lines,cart.coupon,settings.currency_exponent,customer=cart.owner,return_details=True)
    gross=sum((money(l['price'],settings.currency_exponent)*l['quantity'] for l in lines),Decimal(0))
    discount=sum(discounts,Decimal(0));net=gross-discount
    method,fee=quote_delivery(method_id,area_id,net);fee=money(fee,settings.currency_exponent)
    result={'currency':settings.currency,'exponent':settings.currency_exponent,'settings_revision':settings.revision,
        'gross':str(gross),'discount':str(discount),'net':str(net),'delivery_fee':str(fee),'tax':'0','total':str(net+fee),
        'method_id':str(method.id),'area_id':str(area_id) if area_id else None,'promotions':promo_ids,'promotion_calculation':detail,
        'lines':[{'variant_id':str(l['variant'].id),'sku':l['variant'].sku,'quantity':l['quantity'],
                  'gross':str(money(l['price'],settings.currency_exponent)*l['quantity']),'discount':str(discounts[i]),
                  'net':str(money(l['price'],settings.currency_exponent)*l['quantity']-discounts[i]),'unit_net':detail['unit_net'][i],
                  'name':l['snapshot']['name'],'name_ar':l['snapshot'].get('name_ar',''),
                  'category':l['snapshot']['category'],'brand':l['snapshot']['brand']} for i,l in enumerate(lines)]}
    return result

def make_quote(cart,method_id,area_id=None):
    data=totals(cart,method_id,area_id)
    quote=Quote.objects.create(cart=cart,cart_version=cart.version,data=data,digest=digest(data),expires_at=timezone.now()+timedelta(minutes=10))
    Event.objects.get_or_create(key=f'checkout:{cart.id}:{cart.version}:{cart.shopping_session_id or "unattributed"}',defaults={'kind':'begin_checkout','shopping_session_id':cart.shopping_session_id,
        'data':{'cart_id':str(cart.id),'version':cart.version,'quote_id':str(quote.id),'net':data['net'],'currency':data['currency']}})
    if cart.shopping_session_id:
        from apps.analytics.models import ShoppingSession
        ShoppingSession.objects.filter(pk=cart.shopping_session_id).update(qualified=True)
    return quote

@transaction.atomic
def accept(order):
    if order.state!='pending':return order
    # Consistent promotion-before-stock order matches placement and cancellation.
    list(order.promotions.select_for_update().order_by('id'))
    for item in order.items.order_by('variant_id'):
        move(item.variant_id,f'accept:{order.id}:{item.id}','Order accepted',reserved=-item.quantity,committed=item.quantity)
    for p in order.promotions.select_for_update().order_by('id'):
        p.held=max(0,p.held-1);p.used+=1;p.save()
    Redemption.objects.filter(order=order,state='held').update(state='used')
    order.state='processing';order.accepted_at=timezone.now();order.expires_at=None;order.save()
    History.objects.create(order=order,action='accepted')
    Event.objects.get_or_create(key='purchase:'+str(order.id),defaults={'kind':'purchase','shopping_session_id':order.shopping_session_id,'order':order,'data':{'total':str(order.total),'currency':order.currency}})
    Outbox.objects.get_or_create(key='accepted:'+str(order.id),defaults={'event_type':'order.accepted','payload':{'order_id':str(order.id)}})
    return order

@transaction.atomic
def place_order(request,data,key):
    if not key or len(key)>100:raise ValidationError('A valid Idempotency-Key is required.')
    session=request.session.session_key or ''
    owner=str(request.user.id) if request.user.is_authenticated else session
    scoped_key=owner+':'+key;body_hash=digest(data)
    existing=Order.objects.filter(idempotency_key=scoped_key).first()
    if existing:
        if existing.request_hash!=body_hash:raise Conflict('Idempotency key reused with different data.')
        return existing
    try:quote=Quote.objects.select_related('cart').get(id=data['quote_id'])
    except (Quote.DoesNotExist,KeyError):raise ValidationError('Invalid quote.')
    cart=Cart.objects.select_for_update().get(pk=quote.cart_id)
    # A concurrent retry can have waited while the first request committed.
    # Re-read after taking the cart lock instead of rejecting its now-closed cart.
    existing=Order.objects.filter(idempotency_key=scoped_key).first()
    if existing:
        if existing.request_hash!=body_hash:raise Conflict('Idempotency key reused with different data.')
        return existing
    if not ((request.user.is_authenticated and cart.owner_id==request.user.id) or (not cart.owner_id and cart.session_key==session)):
        raise PermissionDenied()
    if not cart.active or quote.cart_version!=cart.version or quote.expires_at<=timezone.now():raise Conflict('Quote expired or cart changed.')
    # Serializes the first transaction against currency/configuration changes.
    StoreSettings.objects.select_for_update().get(pk=StoreSettings.current().pk)
    # Serialize all promotion limits before re-quoting. Narrower locks can follow profiling.
    list(Promotion.objects.select_for_update().order_by('id'))
    variants=set(cart.items.values_list('variant_id',flat=True))
    from uuid import UUID
    for group in cart.bundles.select_related('promotion'):
        variants.update(UUID(v) for v in group.promotion.rules.get('components',{}))
    variants=sorted(variants)
    list(Balance.objects.select_for_update().filter(variant_id__in=variants).order_by('variant_id'))
    current=totals(cart,quote.data['method_id'],quote.data['area_id'])
    if digest(current)!=quote.digest:raise Conflict('Prices, promotions or delivery changed. Request a new quote.')
    contact=data.get('contact',{})
    if not isinstance(contact,dict):raise ValidationError('contact must be an object.')
    from django.core.validators import validate_email
    validate_email(contact.get('email',''))
    if not contact.get('name') or not contact.get('phone'):raise ValidationError('Name, email and phone are required.')
    cfg=StoreSettings.current();method=data.get('payment_method','cod')
    from apps.payments.adapters import card_enabled
    if method not in ['cod','bank','card'] or (method=='card' and not card_enabled()):raise ValidationError('Payment method is not configured.')
    if (method=='cod' and not cfg.cod_enabled) or (method=='bank' and not cfg.bank_enabled):raise ValidationError('Payment method disabled.')
    address=data.get('address',{})
    if data.get('address_id'):
        if not request.user.is_authenticated:raise PermissionDenied('Saved addresses require sign-in.')
        from apps.customers.models import Address
        from django.shortcuts import get_object_or_404
        address=get_object_or_404(Address,pk=data['address_id'],owner=request.user).data
    if not isinstance(address,dict):raise ValidationError('address must be an object.')
    address=dict(address)
    from apps.delivery.models import Method
    delivery=Method.objects.get(id=current['method_id'])
    if delivery.kind!='pickup' and not address.get('line1'):raise ValidationError('Delivery address is required.')
    if delivery.kind!='pickup':
        if address.get('area_id') and address['area_id']!=current['area_id']:raise Conflict('Address area differs from quoted delivery area. Request a new quote.')
        address['area_id']=current['area_id']
    order=Order.objects.create(owner=request.user if request.user.is_authenticated else None,session_key=session,cart=cart,shopping_session_id=cart.shopping_session_id,
        contact={k:str(contact[k])[:250] for k in ['name','email','phone']},address=address,
        business_snapshot={'name':cfg.business_name,'address':cfg.address,'phone':cfg.phone,'email':cfg.email},
        currency=cfg.currency,exponent=cfg.currency_exponent,method=delivery,payment_method=method,
        gross=current['gross'],discount=current['discount'],delivery_fee=current['delivery_fee'],total=current['total'],
        idempotency_key=scoped_key,request_hash=body_hash,expires_at=timezone.now()+timedelta(hours=24))
    for line in current['lines']:
        item=OrderItem.objects.create(order=order,variant_id=line['variant_id'],snapshot=line,quantity=line['quantity'],gross=line['gross'],discount=line['discount'],net=line['net'])
        move(item.variant_id,f'reserve:{order.id}:{item.id}','Checkout reservation',reserved=item.quantity)
    for p in Promotion.objects.filter(id__in=current['promotions']):
        p.held+=1;p.save();order.promotions.add(p)
        Redemption.objects.create(promotion=p,order=order,customer=order.owner)
    cart.active=False;cart.save()
    History.objects.create(order=order,action='placed')
    if method=='card':
        from django.conf import settings as runtime_settings
        from apps.payments.models import PaymentAttempt
        PaymentAttempt.objects.create(order=order,provider=runtime_settings.CARD_PROVIDER)
    if Decimal(current['total'])==0:
        order.payment_state='not_required';order.save();accept(order)
    elif method=='cod':accept(order)
    return order

@transaction.atomic
def transition(order_id,action,actor=None,reason='',*,only_if_expired=False,payment_resolved=False):
    order=Order.objects.select_for_update().get(pk=order_id)
    if only_if_expired and (order.state!='pending' or not order.expires_at or order.expires_at>timezone.now()):
        return order
    if action=='cancel':
        if order.state=='cancelled':return order
        if order.payment_method=='card' and order.state=='pending' and not payment_resolved:
            from apps.payments.models import PaymentAttempt
            attempt=PaymentAttempt.objects.select_for_update().get(order=order)
            if attempt.state not in ['created','failed']:raise Conflict('Reconcile pending or unknown card payment before cancellation.')
            if attempt.state=='created':attempt.state='failed';attempt.issue='cancelled_before_provider_creation';attempt.save()
        if order.departed_at:raise ValidationError('Departed orders require an explicit delivery exception workflow; no automatic restock.')
        if order.state not in ['pending','processing','ready_for_pickup']:raise ValidationError('Cannot cancel this state.')
        field='reserved' if order.state=='pending' else 'committed'
        list(order.promotions.select_for_update().order_by('id'))
        for item in order.items.order_by('variant_id'):
            move(item.variant_id,f'cancel:{order.id}:{item.id}','Order cancelled',**{field:-item.quantity},actor=actor)
        if order.state=='pending':
            for p in order.promotions.select_for_update().order_by('id'):
                p.held=max(0,p.held-1);p.save()
            Redemption.objects.filter(order=order,state='held').update(state='released')
        order.state='cancelled';order.cancelled_at=timezone.now();order.expires_at=None
    elif action=='ready_for_pickup' and order.state=='processing' and order.method.kind=='pickup':order.state=action
    elif action in ['shipped','collected']:
        expected='ready_for_pickup' if action=='collected' else 'processing'
        if order.state!=expected or ((order.method.kind=='pickup')!=(action=='collected')):raise ValidationError('Invalid fulfillment transition.')
        if action=='collected' and order.payment_state not in ['paid','not_required','partially_refunded']:raise ValidationError('Record payment collection first.')
        for item in order.items.order_by('variant_id'):
            move(item.variant_id,f'depart:{order.id}:{item.id}','Goods departed',on_hand=-item.quantity,committed=-item.quantity,actor=actor)
        order.state=action;order.departed_at=timezone.now()
    elif action=='delivered' and order.state=='shipped':
        if order.payment_state not in ['paid','not_required','partially_refunded']:raise ValidationError('Record payment collection first.')
        order.state='delivered'
    else:raise ValidationError('Invalid state transition.')
    order.save();History.objects.create(order=order,action=action,actor=actor,reason=reason)
    event_action='cancelled' if action=='cancel' else action
    if event_action in ['cancelled','shipped','delivered','collected']:
        Outbox.objects.get_or_create(key=f'{event_action}:{order.id}',defaults={'event_type':f'order.{event_action}','payload':{'order_id':str(order.id)}})
    return order

@transaction.atomic
def restock(order_id,item_id,quantity,key,actor):
    order=Order.objects.select_for_update().get(pk=order_id)
    item=order.items.select_for_update().get(pk=item_id)
    from apps.inventory.models import Movement
    existing=Movement.objects.filter(operation_key='restock:'+key).first()
    if existing:
        if existing.variant_id!=item.variant_id or existing.on_hand_delta!=quantity:raise Conflict('Key already used.')
        return item
    if not order.departed_at or quantity<=0 or quantity>item.quantity-item.restocked:raise ValidationError('Restock exceeds unreturned departed quantity.')
    move(item.variant_id,'restock:'+key,'Admin received returned goods',on_hand=quantity,actor=actor)
    item.restocked+=quantity;item.save();History.objects.create(order=order,action='restocked',actor=actor,reason=str(quantity))
    return item

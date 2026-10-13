import base64
import hashlib
import hmac
import json
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock,patch
import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from apps.catalog.models import Product
from apps.catalog.services import create_variant,publish
from apps.promotions.models import Promotion,Redemption
from apps.promotions.services import calculate
from apps.analytics.models import ShoppingSession,Event
from apps.analytics.services import dashboard
from apps.orders.models import Order
from apps.orders.services import transition
from apps.payments.models import PaymentAttempt,Capture
from apps.payments.adapters import PaymentResult,ProviderUnavailable
from apps.payments.adapters import PaymentRequest,InvalidProviderResponse
from apps.payments import card
from apps.payments.skipcash import SkipCashAdapter,signature,WEBHOOK_FIELDS,CREATE_FIELDS
from apps.payments.services import record_capture,request_item_refund,confirm_refund
from common.api import Conflict
from test_commerce import setup,checkout

pytestmark=pytest.mark.django_db

def second_product(category,price='40'):
    p=Product.objects.create(code='second',name='Second',name_ar='ثاني',category=category)
    v=create_variant(p,'SECOND',price,stock=20);publish(p);return v

def line(v,quantity=1):return {'variant':v,'quantity':quantity,'price':str(v.price),'sale_price':None}

def test_explicit_bundle_allocates_exactly_and_does_not_auto_apply(setup):
    _,p,v,method,_=setup;v.price=Decimal('80');v.save();publish(p)
    other=second_product(p.category)
    promo=Promotion.objects.create(name='Bundle',kind='bundle',priority=800,enabled=True,
        rules={'components':{str(v.id):1,str(other.id):1},'price':'100'})
    discounts,_=calculate([line(v),line(other)]);assert discounts==[0,0]
    c=APIClient();c.post('/api/v1/cart/bundles',{'promotion_id':str(promo.id),'quantity':1},format='json')
    r=c.post('/api/v1/checkout/quote',{'method_id':str(method.id)},format='json')
    assert r.status_code==200,r.data
    assert Decimal(r.data['discount'])==20
    assert sorted(Decimal(x['discount']) for x in r.data['lines'])==[Decimal('6.67'),Decimal('13.33')]
    body={'quote_id':r.data['id'],'payment_method':'cod','contact':{'name':'Buyer','email':'b@example.invalid','phone':'123'}}
    placed=c.post('/api/v1/checkout/orders',body,format='json',HTTP_IDEMPOTENCY_KEY='bundle')
    assert placed.status_code==201,placed.data
    assert Redemption.objects.get(promotion=promo).state=='used'
    assert Order.objects.get(pk=placed.data['id']).items.count()==2

def test_bxgy_distinct_scopes_and_no_reused_units(setup):
    _,p,v,_,_=setup;other=second_product(p.category)
    Promotion.objects.create(name='Buy main get accessory',kind='bxgy',priority=700,value=100,enabled=True,
        rules={'buy':1,'get':1,'max_applications':2,'qualifier_scope':{'variants':[str(v.id)]},'reward_scope':{'variants':[str(other.id)]}})
    discount,_=calculate([line(v),line(other,2)])
    assert discount==[0,Decimal(40)]

def test_customer_coupon_limit_and_guests(setup):
    _,_,v,method,user=setup
    promo=Promotion.objects.create(name='Limited',kind='coupon',coupon_code='ONCE',enabled=True,value=10,per_customer_limit=1)
    with pytest.raises(ValidationError):calculate([line(v)],'ONCE')
    assert calculate([line(v)],'ONCE',customer=user)[0]==[Decimal(10)]
    order,_=checkout(APIClient(),v,method)
    Redemption.objects.create(promotion=promo,order=order,customer=user,state='held')
    with pytest.raises(ValidationError):calculate([line(v)],'ONCE',customer=user)

def test_qualified_consent_sessions_and_purchase_dedup(setup):
    _,p,v,method,_=setup;c=APIClient()
    payload={'product_id':str(p.id),'page_view_id':str(uuid.uuid4())}
    assert c.post('/api/v1/analytics/product-view',payload,format='json').data['recorded'] is False
    c.post('/api/v1/analytics/consent',{'consent':True},format='json')
    c.post('/api/v1/analytics/product-view',payload,format='json');c.post('/api/v1/analytics/product-view',payload,format='json')
    assert Event.objects.filter(kind='product_view').count()==1
    checkout(c,v,method)
    report=dashboard({})
    assert report['qualified_sessions']==1 and report['attributed_purchases']==1
    assert Decimal(report['conversion'])==100
    assert report['sales']=='200.000000' and report['best_selling_products'][0]['quantity']==2
    assert sum(Decimal(r['sales']) for r in report['sales_by_category'])==Decimal(report['sales'])

def test_idle_session_rollover_and_bot_exclusion(setup):
    _,p,_,_,_=setup;c=APIClient()
    c.post('/api/v1/analytics/consent',{'consent':True},format='json')
    def view():return c.post('/api/v1/analytics/product-view',{'product_id':str(p.id),'page_view_id':str(uuid.uuid4())},format='json')
    view();ShoppingSession.objects.update(last_seen=timezone.now()-timedelta(minutes=31));view()
    assert ShoppingSession.objects.count()==2
    bot=APIClient(HTTP_USER_AGENT='ExampleBot');bot.post('/api/v1/analytics/consent',{'consent':True},format='json')
    assert bot.post('/api/v1/analytics/product-view',{'product_id':str(p.id),'page_view_id':str(uuid.uuid4())},format='json').data['recorded'] is False

def test_late_purchase_is_outside_cohort_window(setup):
    _,p,v,method,_=setup;c=APIClient();c.post('/api/v1/analytics/consent',{'consent':True},format='json')
    order,_=checkout(c,v,method)
    ShoppingSession.objects.filter(pk=order.shopping_session_id).update(created_at=timezone.now()-timedelta(days=8))
    report=dashboard({})
    assert report['attributed_purchases']==0 and report['outside_window_orders']==1

def test_item_refunds_use_original_unit_price_and_do_not_restock(setup):
    _,p,v,method,admin=setup
    order,_=checkout(APIClient(),v,method);record_capture(order.id,'cash','capture',admin)
    transition(order.id,'ready_for_pickup');transition(order.id,'collected')
    item=order.items.first();v.price=1;v.save();publish(p)
    first=request_item_refund(order.id,[{'order_item_id':str(item.id),'quantity':1}],0,'Returned','refund-a',admin)
    assert first.amount==100
    confirm_refund(first.id,'portal-reference-a',admin)
    second=request_item_refund(order.id,[{'order_item_id':str(item.id),'quantity':1}],0,'Returned','refund-b',admin)
    assert second.amount==100
    with pytest.raises(ValidationError):request_item_refund(order.id,[{'order_item_id':str(item.id),'quantity':1}],0,'Again','refund-c',admin)
    item.refresh_from_db();assert item.restocked==0

def card_order(setup):
    cfg,_,variant,method,_=setup;cfg.bank_enabled=True;cfg.save()
    order,_=checkout(APIClient(),variant,method,payment='bank')
    order.payment_method='card';order.save()
    return order,PaymentAttempt.objects.create(order=order,provider='skipcash')

def result(order,attempt,state='paid',**changes):
    values=dict(reference=str(uuid.UUID(int=10)),state=state,amount=order.total,currency=order.currency,merchant_reference=str(attempt.id))
    values.update(changes);return PaymentResult(**values)

def test_card_reconciliation_is_idempotent_and_monotonic(setup):
    order,attempt=card_order(setup)
    card.apply_result(attempt.id,result(order,attempt));card.apply_result(attempt.id,result(order,attempt))
    card.apply_result(attempt.id,result(order,attempt,'pending'))
    card.apply_result(attempt.id,result(order,attempt,'failed'))
    order.refresh_from_db();attempt.refresh_from_db()
    assert order.state=='processing' and order.payment_state=='paid' and attempt.state=='paid'
    assert Capture.objects.filter(order=order).count()==1
    assert Event.objects.filter(order=order,kind='purchase').count()==1

@pytest.mark.parametrize('change',[{'amount':Decimal(1)},{'currency':'USD'},{'merchant_reference':str(uuid.uuid4())}])
def test_mismatched_gateway_state_cannot_mark_paid(setup,change):
    order,attempt=card_order(setup);card.apply_result(attempt.id,result(order,attempt,**change))
    order.refresh_from_db();attempt.refresh_from_db()
    assert order.state=='pending' and not Capture.objects.filter(order=order).exists()
    assert attempt.issue=='amount_currency_or_reference_mismatch'

def test_unknown_create_never_blindly_retries_or_releases_stock(setup):
    order,attempt=card_order(setup)
    adapter=Mock();adapter.create_payment.side_effect=ProviderUnavailable('timeout')
    with patch('apps.payments.card.get_adapter',return_value=adapter):
        card.start(order.id);card.start(order.id)
    assert adapter.create_payment.call_count==1
    attempt.refresh_from_db();assert attempt.state=='unknown'
    with pytest.raises(Conflict):transition(order.id,'cancel')

def test_failed_card_releases_reservation_and_late_capture_goes_to_exception(setup):
    order,attempt=card_order(setup)
    card.apply_result(attempt.id,result(order,attempt,'failed'))
    order.refresh_from_db();assert order.state=='cancelled'
    card.apply_result(attempt.id,result(order,attempt))
    order.refresh_from_db();assert order.payment_state=='paid_exception' and order.state=='cancelled'
    assert Capture.objects.filter(order=order).count()==1

def test_skipcash_signature_contract_and_invalid_signature(setup,settings):
    settings.SKIPCASH_WEBHOOK_KEY='fake-test-key'
    payload={'paymentId':str(uuid.UUID(int=10)),'amount':'200.00','statusId':2,'transactionId':str(uuid.UUID(int=11))}
    canonical=f"PaymentId={payload['paymentId']},Amount=200.00,StatusId=2,TransactionId={payload['transactionId']}"
    expected=base64.b64encode(hmac.new(b'fake-test-key',canonical.encode(),hashlib.sha256).digest()).decode()
    assert signature(payload,WEBHOOK_FIELDS,'fake-test-key')==expected
    assert SkipCashAdapter().verify_and_parse_webhook(json.dumps(payload).encode(),{'Authorization':expected})==(payload['paymentId'],payload['transactionId'])
    response=APIClient().post('/api/v1/payments/webhooks/skipcash',payload,format='json',HTTP_AUTHORIZATION='invalid')
    assert response.status_code==401

def test_webhook_replays_book_one_capture(setup,settings):
    settings.SKIPCASH_WEBHOOK_KEY='fake-test-key'
    order,attempt=card_order(setup)
    payload={'paymentId':str(uuid.UUID(int=10)),'amount':'200.00','statusId':2,'transactionId':str(attempt.id)}
    body=json.dumps(payload).encode();auth=signature(payload,WEBHOOK_FIELDS,settings.SKIPCASH_WEBHOOK_KEY)
    with patch.object(SkipCashAdapter,'retrieve_payment',return_value=result(order,attempt)) as fetch:
        for _ in range(2):
            response=APIClient().post('/api/v1/payments/webhooks/skipcash',body,content_type='application/json',HTTP_AUTHORIZATION=auth)
            assert response.status_code==200
        assert fetch.call_count==1
    assert Capture.objects.filter(order=order).count()==1

def test_skipcash_http_contract_signs_without_sending_card_data(setup,settings):
    for key in ['SKIPCASH_CLIENT_ID','SKIPCASH_KEY_ID','SKIPCASH_KEY_SECRET','SKIPCASH_WEBHOOK_KEY']:setattr(settings,key,'test-only')
    settings.SKIPCASH_ENV='sandbox'
    identifier=str(uuid.UUID(int=7));provider_id=str(uuid.UUID(int=8))
    response=Mock(status_code=200,content=json.dumps({'resultObj':{'id':provider_id,'statusId':0,'amount':'10.00','currency':'QAR','transactionId':identifier,
        'payUrl':f'https://skipcashtest.azurewebsites.net/pay/{provider_id}'}}).encode())
    request=PaymentRequest(identifier,Decimal('10'),'QAR',identifier,'https://example.invalid/return',{'name':'Test Buyer','email':'test@example.invalid','phone':'00000000'})
    with patch('apps.payments.skipcash.requests.request',return_value=response) as http:
        result=SkipCashAdapter().create_payment(request)
    sent=http.call_args.kwargs
    assert sent['json']['transactionId']==identifier and sent['json']['uid']==identifier
    assert sent['headers']['Authorization']==signature(sent['json'],CREATE_FIELDS,'test-only')
    assert set(sent['json'])=={'uid','keyId','amount','firstName','lastName','email','phone','transactionId'}
    assert sent['allow_redirects'] is False and result.state=='pending'

def test_skipcash_does_not_redirect_to_untrusted_host(settings):
    with pytest.raises(InvalidProviderResponse):
        SkipCashAdapter()._result({'id':str(uuid.uuid4()),'amount':'20','currency':'QAR','statusId':0,'payUrl':'https://evil.example/checkout'})

def test_password_reset_is_single_use_and_revokes_old_sessions(settings):
    from apps.identity.models import User
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    user=User.objects.create_user(username='reset@example.invalid',email='reset@example.invalid',password='Old-password-44221!')
    old=APIClient();old.force_login(user)
    token=default_token_generator.make_token(user)
    body={'uid':urlsafe_base64_encode(str(user.id).encode()),'token':token,'password':'New-password-88772!'}
    client=APIClient()
    assert client.post('/api/v1/auth/password/reset-confirm',body,format='json').status_code==200
    assert client.post('/api/v1/auth/password/reset-confirm',body,format='json').status_code==400
    assert old.get('/api/v1/auth/session').status_code==403

def test_staff_session_absolute_expiry(setup):
    import time
    *_,admin=setup;client=APIClient();client.force_login(admin)
    session=client.session;session['staff_mfa']=True;session['authenticated_at']=time.time()-13*3600;session['last_activity']=time.time();session.save()
    assert client.get('/api/v1/admin/products').status_code==403

def test_delivery_bands_are_non_overlapping_and_exclusive(setup):
    from apps.delivery.models import Method,Rule,Area,Zone
    from apps.delivery.services import quote_delivery
    zone=Zone.objects.create(code='z',name='Zone');area=Area.objects.create(code='a',name='Area',zone=zone)
    method=Method.objects.create(code='delivery',name='Delivery',kind='standard')
    low=Rule.objects.create(method=method,area=area,minimum=0,upper_bound=100,fee=20)
    high=Rule(method=method,area=area,minimum=100,fee=10);high.full_clean();high.save()
    overlap=Rule(method=method,area=area,minimum=50,upper_bound=150,fee=15)
    with pytest.raises(Exception):overlap.full_clean()
    assert quote_delivery(method.id,area.id,Decimal('99.99'))[1]==20
    assert quote_delivery(method.id,area.id,Decimal('100'))[1]==10

def test_outbox_delivery_is_recorded_and_not_repeated(setup,settings):
    from django.core import mail
    from apps.operations.tasks import deliver_outbox
    from apps.operations.models import Outbox
    settings.EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    _,_,v,method,_=setup;order,_=checkout(APIClient(),v,method)
    assert deliver_outbox()==1 and deliver_outbox()==0
    event=Outbox.objects.get(key='accepted:'+str(order.id))
    assert event.delivered_at and event.attempts==1 and len(mail.outbox)==1
    assert 'تم تأكيد الطلب' in mail.outbox[0].body

def test_outbox_failure_is_retryable_and_does_not_log_secrets(setup):
    from apps.operations.tasks import deliver_outbox
    from apps.operations.models import Outbox
    _,_,v,method,_=setup;order,_=checkout(APIClient(),v,method)
    with patch('apps.operations.tasks.send_event',side_effect=RuntimeError('smtp password=secret')):
        assert deliver_outbox()==0
    event=Outbox.objects.get(key='accepted:'+str(order.id))
    assert event.last_error=='delivery_failed' and event.retry_at>timezone.now() and event.delivered_at is None

def test_json_arrays_rejected_before_domain_logic():
    response=APIClient().post('/api/v1/cart',['invalid'],format='json')
    assert response.status_code==400

def test_addresses_are_owned_and_owner_input_cannot_reassign(setup):
    from apps.identity.models import User
    from apps.customers.models import Address
    first=User.objects.create_user(username='one',email='one@example.invalid')
    second=User.objects.create_user(username='two',email='two@example.invalid')
    client=APIClient();client.force_login(first)
    response=client.post('/api/v1/account/addresses',{'label':'Home','owner':str(second.id),'data':{'line1':'Example street'}},format='json')
    assert response.status_code==201,response.data
    address=Address.objects.get(pk=response.data['id']);assert address.owner==first
    other=APIClient();other.force_login(second)
    assert other.get('/api/v1/account/addresses/'+str(address.id)).status_code==404
    assert other.patch('/api/v1/account/addresses/'+str(address.id),{'label':'Hijack'},format='json').status_code==404

def test_typed_attributes_and_published_search(setup):
    from apps.catalog.models import Attribute
    _,product,variant,_,admin=setup
    Attribute.objects.create(code='wattage',name='Wattage',data_type='number')
    client=APIClient();client.force_login(admin);session=client.session;session['staff_mfa']=True;session.save()
    route=f'/api/v1/admin/products/{product.id}/attributes'
    assert client.patch(route,{'values':{'wattage':'12W'}},format='json').status_code==400
    assert client.patch(route,{'values':{'wattage':12}},format='json').status_code==200
    publish(product)
    public=APIClient()
    assert public.get('/api/v1/store/products',{'attr.wattage':'12.0'}).data['count']==1
    assert public.get('/api/v1/store/products',{'attr.wattage':'13'}).data['count']==0
    assert public.get('/api/v1/store/products',{'limit':1,'page':2}).data['results']==[]

def test_category_parent_filter_and_arabic_diacritics(setup):
    from apps.catalog.models import Category
    _,product,_,_,_=setup
    parent=Category.objects.create(code='parent',name='Parent')
    product.category.parent=parent;product.category.save()
    product.name_ar='مُنْتَج';product.save();publish(product)
    response=APIClient().get('/api/v1/store/products',{'q':'منتج','category':'parent'})
    assert response.status_code==200 and response.data['count']==1

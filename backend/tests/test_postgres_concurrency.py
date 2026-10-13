"""Release-gate test: deliberately skipped on SQLite, which has different locks."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from django.db import connection, connections
from rest_framework.exceptions import ValidationError
from apps.inventory.services import move
from apps.inventory.models import Balance
from test_commerce import setup

def require_postgres():
    if connection.vendor!='postgresql':pytest.skip('Requires PostgreSQL row locks')

def parallel(function):
    barrier=Barrier(2)
    def run(index):
        try:
            barrier.wait(timeout=10)
            return function(index)
        finally:connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(run,[0,1]))


@pytest.mark.django_db(transaction=True)
def test_simultaneous_reservations_cannot_oversell(setup):
    if connection.vendor!='postgresql':pytest.skip('Requires PostgreSQL row locks')
    _,_,variant,_,_=setup
    barrier=Barrier(2)
    def reserve(key):
        try:
            barrier.wait(timeout=10)
            move(variant.id,key,'Concurrent test reservation',reserved=8)
            return 'reserved'
        except ValidationError:
            return 'unavailable'
        finally:
            connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(reserve,['concurrency-a','concurrency-b']))
    assert sorted(results)==['reserved','unavailable']
    balance=Balance.objects.get(variant=variant)
    assert balance.reserved==8 and balance.available==2

@pytest.mark.django_db(transaction=True)
def test_concurrent_checkout_retry_returns_one_order(setup):
    require_postgres()
    from rest_framework.test import APIClient
    from apps.orders.models import Order
    _,_,variant,method,_=setup
    base=APIClient();base.post('/api/v1/cart',{'variant_id':str(variant.id),'quantity':2},format='json')
    quote=base.post('/api/v1/checkout/quote',{'method_id':str(method.id)},format='json').data
    body={'quote_id':quote['id'],'payment_method':'cod','contact':{'name':'Buyer','email':'race@example.invalid','phone':'123'}}
    def place(index):
        client=APIClient();client.cookies=base.cookies.copy()
        response=client.post('/api/v1/checkout/orders',body,format='json',HTTP_IDEMPOTENCY_KEY='same-concurrent-key')
        return response.status_code,response.data.get('id')
    results=parallel(place)
    assert [r[0] for r in results]==[201,201] and results[0][1]==results[1][1]
    assert Order.objects.count()==1 and Balance.objects.get(variant=variant).committed==2

@pytest.mark.django_db(transaction=True)
def test_customer_coupon_limit_is_atomic_across_carts(setup):
    require_postgres()
    from rest_framework.test import APIClient
    from apps.orders.models import Cart,CartItem,Order
    from apps.orders.services import make_quote
    from apps.promotions.models import Promotion
    _,_,variant,method,customer=setup
    promo=Promotion.objects.create(name='One use',kind='coupon',coupon_code='ONE',enabled=True,value=10,per_customer_limit=1)
    clients=[];bodies=[]
    for i in range(2):
        client=APIClient();client.force_login(customer);clients.append(client)
        cart=Cart.objects.create(owner=customer,session_key=client.session.session_key,coupon='ONE')
        CartItem.objects.create(cart=cart,variant=variant,quantity=1)
        quote=make_quote(cart,method.id)
        bodies.append({'quote_id':str(quote.id),'payment_method':'cod','contact':{'name':'Buyer','email':'race@example.invalid','phone':'123'}})
    def place(index):return clients[index].post('/api/v1/checkout/orders',bodies[index],format='json',HTTP_IDEMPOTENCY_KEY=f'coupon-{index}').status_code
    results=parallel(place)
    assert results.count(201)==1 and all(code in [201,400,409] for code in results)
    promo.refresh_from_db();assert promo.used==1 and promo.held==0 and Order.objects.count()==1

@pytest.mark.django_db(transaction=True)
def test_outbox_claim_prevents_two_workers_sending_same_event(setup):
    require_postgres()
    import time
    from unittest.mock import patch
    from rest_framework.test import APIClient
    from test_commerce import checkout
    from apps.operations.tasks import deliver_outbox
    from apps.operations.models import Outbox
    _,_,variant,method,_=setup;checkout(APIClient(),variant,method)
    sent=[]
    def send(event):sent.append(event.id);time.sleep(0.2)
    with patch('apps.operations.tasks.send_event',side_effect=send):results=parallel(lambda _:deliver_outbox())
    assert sum(results)==1 and len(sent)==1 and Outbox.objects.filter(delivered_at__isnull=False).count()==1

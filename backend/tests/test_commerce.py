import json
from decimal import Decimal
from datetime import timedelta,time
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from apps.identity.models import User,Role
from apps.catalog.models import Product,Category,Brand,Attribute,AttributeOption,Variant
from apps.catalog.services import create_variant,publish
from apps.configuration.models import StoreSettings
from apps.delivery.models import Method,Rule,Zone,Area
from apps.inventory.models import Balance,Movement
from apps.inventory.services import adjust,move
from apps.orders.models import Order,Cart,CartItem
from apps.orders.services import make_quote,transition,restock
from apps.payments.services import record_capture,request_refund,confirm_refund
from apps.promotions.models import Promotion
from apps.promotions.services import calculate
from apps.imports.services import upload,confirm
from apps.delivery.services import quote_delivery
from common.money import allocate

pytestmark=pytest.mark.django_db

@pytest.fixture
def setup():
    cfg=StoreSettings.current()
    cat=Category.objects.create(code='general',name='General',name_ar='عام')
    p=Product.objects.create(code='item',name='Item',name_ar='منتج',category=cat)
    v=create_variant(p,'SKU-1',Decimal('100'),stock=10);publish(p)
    pickup=Method.objects.create(code='pickup',name='Pickup',kind='pickup')
    admin=User.objects.create_superuser(username='admin@example.invalid',email='admin@example.invalid',password='testing-long-password')
    return cfg,p,v,pickup,admin

def checkout(client,variant,method,payment='cod',key='order-1'):
    r=client.post('/api/v1/cart',{'variant_id':str(variant.id),'quantity':2},format='json');assert r.status_code==200,r.data
    q=client.post('/api/v1/checkout/quote',{'method_id':str(method.id)},format='json');assert q.status_code==200,q.data
    body={'quote_id':q.data['id'],'payment_method':payment,'contact':{'name':'Buyer','email':'buyer@example.invalid','phone':'123456789'},'address':{}}
    r=client.post('/api/v1/checkout/orders',body,format='json',HTTP_IDEMPOTENCY_KEY=key)
    assert r.status_code==201,r.data
    return Order.objects.get(pk=r.data['id']),body

def test_cod_reserve_commit_collect_and_no_double_deduct(setup):
    cfg,p,v,method,admin=setup;client=APIClient();order,body=checkout(client,v,method)
    b=Balance.objects.get(variant=v);assert (b.on_hand,b.reserved,b.committed,b.available)==(10,0,2,8)
    repeated=client.post('/api/v1/checkout/orders',body,format='json',HTTP_IDEMPOTENCY_KEY='order-1');assert repeated.status_code==201
    assert Order.objects.count()==1
    record_capture(order.id,'cash-1','capture-1',admin)
    transition(order.id,'ready_for_pickup',admin);transition(order.id,'collected',admin)
    b.refresh_from_db();assert (b.on_hand,b.committed,b.available)==(8,0,8)

def test_partial_refund_does_not_restock(setup):
    cfg,p,v,method,admin=setup;o,_=checkout(APIClient(),v,method)
    record_capture(o.id,'cash','capture',admin)
    r=request_refund(o.id,'50','Goodwill','refund-1',admin);confirm_refund(r.id,'external-transfer',admin)
    b=Balance.objects.get(variant=v);assert b.on_hand==10 and b.committed==2
    o.refresh_from_db();assert o.payment_state=='partially_refunded'
    with pytest.raises(Exception):request_refund(o.id,'151','Too much','refund-2',admin)

def test_cancel_full_refund_and_separate_restock(setup):
    cfg,p,v,method,admin=setup;o,_=checkout(APIClient(),v,method);record_capture(o.id,'cash','cap',admin)
    with pytest.raises(Exception):request_refund(o.id,'200','Full','rf',admin)
    transition(o.id,'cancel',admin)
    r=request_refund(o.id,'200','Full','rf',admin);confirm_refund(r.id,'sent',admin)
    b=Balance.objects.get(variant=v);assert b.available==10 and b.on_hand==10

def test_explicit_restock_is_bounded_and_idempotent(setup):
    cfg,p,v,method,admin=setup;o,_=checkout(APIClient(),v,method);record_capture(o.id,'cash','cap',admin)
    transition(o.id,'ready_for_pickup',admin);transition(o.id,'collected',admin);i=o.items.first()
    restock(o.id,i.id,1,'return-1',admin);restock(o.id,i.id,1,'return-1',admin)
    assert Balance.objects.get(variant=v).on_hand==9
    with pytest.raises(Exception):restock(o.id,i.id,2,'return-2',admin)

def test_bank_reservation_expires(setup):
    cfg,p,v,method,admin=setup;cfg.bank_enabled=True;cfg.save()
    o,_=checkout(APIClient(),v,method,payment='bank');assert o.state=='pending'
    b=Balance.objects.get(variant=v);assert b.reserved==2 and b.committed==0
    transition(o.id,'cancel',reason='expired');b.refresh_from_db();assert b.available==10
    with pytest.raises(Exception):record_capture(o.id,'late','cap',admin)

def test_guest_order_isolation(setup):
    _,_,v,m,_=setup;c1=APIClient();o,_=checkout(c1,v,m)
    assert c1.get('/api/v1/orders/'+str(o.id)).status_code==200
    assert APIClient().get('/api/v1/orders/'+str(o.id)).status_code==404
    assert APIClient().get('/api/v1/orders/'+str(o.id)+'/invoice').status_code==404

def test_customer_cannot_mutate_admin(setup):
    u=User.objects.create_user(username='customer',email='customer@example.invalid',password='long-pass-test')
    c=APIClient();c.force_login(u)
    assert c.get('/api/v1/admin/products').status_code==403
    assert c.patch('/api/v1/admin/settings',{'currency':'USD'},format='json').status_code==403

def test_staff_requires_mfa_session(setup):
    *_,admin=setup;c=APIClient();c.force_login(admin)
    assert c.get('/api/v1/admin/products').status_code==403
    s=c.session;s['staff_mfa']=True;s.save()
    assert c.get('/api/v1/admin/products').status_code==200

def test_currency_locked_and_tax_zero(setup):
    cfg,p,v,m,admin=setup;o,_=checkout(APIClient(),v,m)
    assert o.tax==0
    cfg.currency='USD'
    with pytest.raises(Exception):cfg.full_clean()

def test_inventory_underflow_and_retry_conflict(setup):
    _,_,v,_,_=setup
    with pytest.raises(Exception):adjust(v.id,-11,'Bad','bad')
    adjust(v.id,3,'Count','count-1');adjust(v.id,3,'Count','count-1')
    assert Balance.objects.get(variant=v).on_hand==13
    with pytest.raises(Exception):adjust(v.id,4,'Count','count-1')

def test_sale_and_coupon_do_not_stack(setup):
    _,p,v,_,_=setup
    p2=Product.objects.create(code='second',name='Second',name_ar='ثاني',category=p.category)
    v2=create_variant(p2,'SKU-2','50',stock=10)
    Promotion.objects.create(name='Coupon',kind='coupon',coupon_code='TEN',discount_type='percent',value=10,enabled=True)
    discounts,_=calculate([{'variant':v,'quantity':1,'price':'100','sale_price':'80'},{'variant':v2,'quantity':1,'price':'50','sale_price':None}],'TEN')
    assert discounts==[Decimal(20),Decimal(5)]

def test_priority_wins_over_larger_discount(setup):
    _,p,v,_,_=setup
    Promotion.objects.create(name='Product',kind='product',priority=400,value=10,enabled=True)
    Promotion.objects.create(name='Brand',kind='brand',priority=200,value=20,enabled=True)
    discounts,_=calculate([{'variant':v,'quantity':1,'price':'100','sale_price':None}])
    assert discounts==[Decimal(10)]

def test_bxgy_no_unit_reuse(setup):
    _,p,v,_,_=setup
    Promotion.objects.create(name='Buy2Get1',kind='bxgy',priority=700,value=100,enabled=True,rules={'buy':2,'get':1})
    discounts,_=calculate([{'variant':v,'quantity':3,'price':'40','sale_price':None}]);assert discounts==[Decimal(40)]

def test_delivery_cutoff_and_net_threshold(setup):
    _,_,_,_,_=setup;z=Zone.objects.create(code='z',name='Zone');a=Area.objects.create(zone=z,code='a',name='Area')
    m=Method.objects.create(code='express',name='Express',kind='express',cutoff=time(12))
    Rule.objects.create(method=m,area=a,fee='15',free_threshold='200')
    now=timezone.now().replace(hour=7,minute=0,second=0,microsecond=0)
    assert quote_delivery(m.id,a.id,Decimal(190),now)[1]==15
    assert quote_delivery(m.id,a.id,Decimal(200),now)[1]==0
    with pytest.raises(Exception):quote_delivery(m.id,a.id,Decimal(200),now.replace(hour=9))

def test_variant_relations_and_duplicate_combination(setup):
    _,p,_,_,_=setup;attr=Attribute.objects.create(code='color',name='Color',data_type='single_select',variant_eligible=True)
    AttributeOption.objects.create(attribute=attr,code='black',label='Black')
    vp=Product.objects.create(code='variable',name='Variable',name_ar='متغير',kind='variable',category=p.category)
    create_variant(vp,'VAR-1','100',{'color':'black'})
    with pytest.raises(Exception):create_variant(vp,'VAR-2','100',{'color':'black'})
    with pytest.raises(Exception):create_variant(vp,'VAR-3','100',{'color':'unknown'})

def test_published_product_does_not_expose_draft_or_cost(setup):
    _,p,v,_,_=setup;p.name='Draft changed';p.save();v.cost_price=Decimal(23);v.save()
    r=APIClient().get('/api/v1/store/products/item');assert r.status_code==200
    assert r.data['name']=='Item' and 'cost_price' not in json.dumps(r.data)

def test_stale_quote_rejects_without_order(setup):
    _,p,v,m,_=setup;c=APIClient();c.post('/api/v1/cart',{'variant_id':str(v.id),'quantity':1},format='json')
    q=c.post('/api/v1/checkout/quote',{'method_id':str(m.id)},format='json')
    v.price=Decimal(200);v.save();publish(p)
    r=c.post('/api/v1/checkout/orders',{'quote_id':q.data['id'],'payment_method':'cod','contact':{'name':'B','email':'b@example.invalid','phone':'1'}},format='json',HTTP_IDEMPOTENCY_KEY='stale')
    assert r.status_code==409 and not Order.objects.exists()

def test_csrf_required_for_anonymous_checkout(setup):
    _,_,v,_,_=setup;c=APIClient(enforce_csrf_checks=True)
    assert c.post('/api/v1/cart',{'variant_id':str(v.id),'quantity':1},format='json').status_code==403

def csv_row(code='new',sku='NEW',stock='3'):
    return f'product_code,product_type,name_en,name_ar,sku,category_code,subcategory_code,price,stock,attributes_json,variant_attributes_json\n{code},simple,New,جديد,{sku},general,,20,{stock},{{}},{{}}\n'.encode()

def test_import_all_or_nothing_and_idempotent(setup):
    _,_,_,_,admin=setup
    valid=csv_row();invalid=valid+'bad,simple,Bad,سيئ,BAD,general,,20,-1,{},{}\n'.encode()
    job=upload(admin,SimpleUploadedFile('bad.csv',invalid));assert job.state=='invalid'
    with pytest.raises(Exception):confirm(job.id,job.plan_hash,admin)
    assert not Product.objects.filter(code='new').exists()
    job=upload(admin,SimpleUploadedFile('valid.csv',valid));assert job.state=='previewed',job.errors
    confirm(job.id,job.plan_hash,admin);confirm(job.id,job.plan_hash,admin)
    assert Variant.objects.filter(sku='NEW').count()==1

def test_import_stale_plan_rejected(setup):
    _,_,v,_,admin=setup;job=upload(admin,SimpleUploadedFile('a.csv',csv_row()))
    adjust(v.id,1,'Count','count')
    with pytest.raises(Exception):confirm(job.id,job.plan_hash,admin)
    assert not Product.objects.filter(code='new').exists()

def test_rounding_allocation_reconciles():
    parts=allocate('20',['80','40']);assert parts==[Decimal('13.33'),Decimal('6.67')]

def test_card_method_not_faked(setup):
    _,_,v,m,_=setup;c=APIClient();c.post('/api/v1/cart',{'variant_id':str(v.id),'quantity':1},format='json')
    q=c.post('/api/v1/checkout/quote',{'method_id':str(m.id)},format='json')
    r=c.post('/api/v1/checkout/orders',{'quote_id':q.data['id'],'payment_method':'card','contact':{'name':'B','email':'b@example.invalid','phone':'1'}},format='json',HTTP_IDEMPOTENCY_KEY='card')
    assert r.status_code==400 and not Order.objects.exists()

def test_currency_update_api_rolls_back(setup):
    cfg,p,v,m,admin=setup;checkout(APIClient(),v,m)
    c=APIClient();c.force_login(admin);session=c.session;session['staff_mfa']=True;session.save()
    r=c.patch('/api/v1/admin/settings',{'currency':'USD'},format='json')
    assert r.status_code==400
    cfg.refresh_from_db();assert cfg.currency=='QAR'

def test_content_role_cannot_refund_or_read_inventory(setup):
    role=Role.objects.create(code='content',name='Content',capabilities=['content.view','content.manage'])
    u=User.objects.create_user(username='content',email='content@example.invalid',is_staff=True,password='long-password-test')
    u.roles.add(role);c=APIClient();c.force_login(u);s=c.session;s['staff_mfa']=True;s.save()
    assert c.get('/api/v1/admin/pages').status_code==200
    assert c.get('/api/v1/admin/inventory').status_code==403

@pytest.mark.parametrize('client,brand,attribute',[('a','Vertex','color'),('b','Current','wattage')])
def test_two_distinct_demo_configurations(client,brand,attribute,settings):
    settings.DEBUG=True
    call_command('bootstrap');call_command('seed_demo',client)
    assert StoreSettings.current().business_name==brand
    assert Product.objects.filter(status='active').count()==2
    assert Variant.objects.count()==3
    assert Attribute.objects.filter(code=attribute).exists()
    assert not User.objects.filter(is_superuser=True,is_active=True).exists()

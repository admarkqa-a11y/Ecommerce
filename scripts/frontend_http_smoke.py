"""Non-destructive GET checks; optional disposable commerce test explicitly enabled.
Run with both Next servers and a disposable seeded backend already running.
"""
import argparse,requests,uuid,html
p=argparse.ArgumentParser();p.add_argument('--store',default='http://127.0.0.1:3000');p.add_argument('--admin',default='http://127.0.0.1:3001');p.add_argument('--disposable-checkout',action='store_true');args=p.parse_args()
s=requests.Session();s.trust_env=False
for path,language,direction in [('/en','en','ltr'),('/ar','ar','rtl')]:
 r=s.get(args.store+path,timeout=20);r.raise_for_status()
 assert f'lang="{language}"' in r.text and f'dir="{direction}"' in r.text
 assert 'store-header' in r.text
assert 'product-card' in s.get(args.store+'/en/shop',timeout=20).text
assert s.get(args.store+'/en/not-a-real-page',timeout=20).status_code==404
assert s.get(args.admin,timeout=20).status_code==200
print('PASS: storefront EN/AR server rendering, RTL, catalog markup, 404 and admin shell.')
def call(method,path,status=200,**kwargs):
 r=s.request(method,args.store+'/api/v1'+path,timeout=20,**kwargs)
 assert r.status_code==status,(path,r.status_code,r.text[:300]);return r.json() if r.content else None
cfg=call('GET','/store/config');products=call('GET','/store/products')['results']
assert cfg['currency'] and products
product_page=s.get(args.store+'/en/products/'+products[0]['code'],timeout=20)
assert product_page.status_code==200 and html.escape(products[0]['name'],quote=False) in product_page.text
assert 'product-detail' in product_page.text
print('PASS: product detail present in server-rendered HTML.')
assert call('GET','/health/ready')['status']=='ready'
if args.disposable_checkout:
 token=call('GET','/auth/csrf')['csrfToken'];s.headers.update({'X-CSRFToken':token,'Origin':args.store})
 variant=next(v for product in products for v in product['variants'] if v['available']>0)
 method=next(m for m in call('GET','/store/delivery-methods') if m['kind']=='pickup')
 call('POST','/analytics/consent',json={'consent':False})
 call('POST','/cart',json={'variant_id':variant['id'],'quantity':1})
 quote=call('POST','/checkout/quote',json={'method_id':method['id']})
 body={'quote_id':quote['id'],'payment_method':'cod','contact':{'name':'Frontend integration test','email':'ui@example.invalid','phone':'00000000'}}
 key=str(uuid.uuid4());order=call('POST','/checkout/orders',201,json=body,headers={'Idempotency-Key':key})
 again=call('POST','/checkout/orders',201,json=body,headers={'Idempotency-Key':key})
 assert order['id']==again['id'] and order['state']=='processing'
 call('GET','/orders/'+order['id'])
 s.cookies.clear();call('GET','/orders/'+order['id'],404)
 print('PASS: Next runtime proxy CSRF/cookies, consent, cart, quote, COD checkout, retry idempotency and guest ownership.')
s.close()

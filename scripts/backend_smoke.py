"""Real HTTP smoke test against a disposable SQLite database and loopback WSGI server."""
import os
import sys
import tempfile
import threading
from pathlib import Path
from wsgiref.simple_server import make_server, WSGIRequestHandler

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))

with tempfile.TemporaryDirectory(prefix='retail-backend-smoke-') as directory:
    # Never use a deployment's database, queue, SMTP credentials or settings.
    os.environ.update(DJANGO_SETTINGS_MODULE='config.settings',ENVIRONMENT='development',
        DATABASE_URL='',SQLITE_PATH=str(Path(directory)/'smoke.sqlite3'),
        ALLOWED_HOSTS='127.0.0.1,localhost',REDIS_URL='',
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    import django
    django.setup()
    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application
    import requests
    call_command('migrate',verbosity=0)
    call_command('bootstrap',verbosity=0)
    call_command('seed_demo','a',verbosity=0)

    class QuietHandler(WSGIRequestHandler):
        def log_message(self,*args):pass

    server=make_server('127.0.0.1',0,get_wsgi_application(),handler_class=QuietHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    session=requests.Session();session.trust_env=False
    origin=f'http://127.0.0.1:{server.server_port}'
    try:
        def call(method,path,status=200,**kwargs):
            response=session.request(method,origin+'/api/v1'+path,timeout=10,**kwargs)
            assert response.status_code==status,(path,response.status_code,response.text[:500])
            return response.json()
        call('GET','/health/ready')
        token=call('GET','/auth/csrf')['csrfToken']
        session.headers['X-CSRFToken']=token
        products=call('GET','/store/products')['results']
        variant=products[0]['variants'][0]
        pickup=next(method for method in call('GET','/store/delivery-methods') if method['kind']=='pickup')
        call('POST','/cart',json={'variant_id':variant['id'],'quantity':1})
        quote=call('POST','/checkout/quote',json={'method_id':pickup['id']})
        body={'quote_id':quote['id'],'payment_method':'cod',
              'contact':{'name':'Smoke Test','email':'smoke@example.invalid','phone':'00000000'}}
        order=call('POST','/checkout/orders',status=201,json=body,headers={'Idempotency-Key':'smoke-order'})
        repeated=call('POST','/checkout/orders',status=201,json=body,headers={'Idempotency-Key':'smoke-order'})
        assert repeated['id']==order['id'] and order['tax']=='0'
        call('GET','/orders/'+order['id'])
        session.cookies.clear()
        call('GET','/orders/'+order['id'],status=404)
        print('PASS: live HTTP readiness, CSRF, catalog, cart, quote, COD order, idempotency, zero tax and guest isolation.')
    finally:
        session.close();server.shutdown();thread.join(timeout=5);server.server_close()

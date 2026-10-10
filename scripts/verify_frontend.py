"""Run built Next apps against a freshly seeded disposable backend.
No deployment DB, SMTP or merchant credentials are used. Creates one synthetic COD order.
"""
import os,sys,tempfile,threading,subprocess,time,requests,argparse
from pathlib import Path
from wsgiref.simple_server import make_server,WSGIRequestHandler
parser=argparse.ArgumentParser();parser.add_argument('--demo',choices=['a','b'],default='a');parser.add_argument('--snapshot-dir',default='');args=parser.parse_args()
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'backend'))
with tempfile.TemporaryDirectory(prefix='retail-ui-verify-') as directory:
 os.environ.update(DJANGO_SETTINGS_MODULE='config.settings',ENVIRONMENT='development',DATABASE_URL='',SQLITE_PATH=directory+'/test.sqlite3',REDIS_URL='',ALLOWED_HOSTS='127.0.0.1,localhost',CSRF_TRUSTED_ORIGINS='http://127.0.0.1:3100,http://127.0.0.1:3101',EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',CARD_ENABLED='false',ANALYTICS_TEST_DEPLOYMENT='true')
 import django;django.setup()
 from django.core.management import call_command
 from django.core.wsgi import get_wsgi_application
 call_command('migrate',verbosity=0);call_command('bootstrap',verbosity=0);call_command('seed_demo',args.demo,verbosity=0)
 class Quiet(WSGIRequestHandler):
  def log_message(self,*args):pass
 server=make_server('127.0.0.1',8100,get_wsgi_application(),handler_class=Quiet)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();processes=[]
 try:
  for name,port in [('storefront',3100),('admin',3101)]:
   env=os.environ.copy();env.update(API_ORIGIN='http://127.0.0.1:8100',API_HTTPS_TERMINATED='false',NEXT_TELEMETRY_DISABLED='1')
   log=open(directory+'/'+name+'.log','w+')
   proc=subprocess.Popen(['node',str(root/'node_modules/next/dist/bin/next'),'start','-H','127.0.0.1','-p',str(port)],cwd=root/'apps'/name,env=env,stdout=log,stderr=log)
   processes.append((proc,log))
  client=requests.Session();client.trust_env=False
  for port in [3100,3101]:
   for attempt in range(80):
    try:
     r=client.get(f'http://127.0.0.1:{port}',timeout=2)
     if r.status_code==200:break
    except requests.RequestException:pass
    time.sleep(.25)
   else:raise RuntimeError('Next server did not become ready.')
  # Search/category links must work on a direct server-rendered page load too.
  catalog=client.get('http://127.0.0.1:3100/api/v1/store/products',timeout=20).json()['results']
  term=catalog[0]['name']
  result=client.get('http://127.0.0.1:3100/en/shop',params={'q':term},timeout=20)
  assert result.status_code==200 and result.text.count('class="product-card"')==1
  empty=client.get('http://127.0.0.1:3100/en/shop',params={'q':'zz-no-such-product-041'},timeout=20)
  assert empty.status_code==200 and 'class="product-card"' not in empty.text
  for language in ['en','ar']:
   home=client.get('http://127.0.0.1:3100/'+language,timeout=20)
   assert home.status_code==200 and 'category-menu' in home.text and 'marketplace-hero' in home.text
   if args.snapshot_dir:
    destination=Path(args.snapshot_dir);destination.mkdir(parents=True,exist_ok=True)
    (destination/(args.demo+'-'+language+'.html')).write_text(home.text)
  print('PASS: direct URL search, empty search results, runtime category navigation and marketplace homepage in both languages.')
  subprocess.run([sys.executable,str(root/'scripts/frontend_http_smoke.py'),'--store','http://127.0.0.1:3100','--admin','http://127.0.0.1:3101','--disposable-checkout'],check=True)
  import secrets,pyotp
  from apps.identity.models import User
  from apps.identity.views import cipher
  from apps.configuration.models import StoreSettings
  password=secrets.token_urlsafe(24);secret=pyotp.random_base32()
  user=User.objects.create_superuser(username='verify-admin@example.invalid',email='verify-admin@example.invalid',password=password)
  user.mfa_secret=cipher().encrypt(secret.encode()).decode();user.save()
  admin=requests.Session();admin.trust_env=False;origin='http://127.0.0.1:3101'
  def admin_call(method,path,**kwargs):
   response=admin.request(method,origin+'/api/v1'+path,timeout=15,**kwargs)
   assert response.status_code in [200,201],(path,response.status_code,response.text[:250])
   return response.json()
  admin.headers.update({'Origin':origin,'X-CSRFToken':admin_call('GET','/auth/csrf')['csrfToken']})
  signed=admin_call('POST','/auth/login',json={'email':user.email,'password':password,'otp':pyotp.TOTP(secret).now(),'admin':True})
  assert signed['staff_mfa']
  admin.headers['X-CSRFToken']=admin_call('GET','/auth/csrf')['csrfToken']
  report=admin_call('GET','/admin/dashboard')
  assert report['orders']==1 and isinstance(report['sales_by_date'],list)
  assert isinstance(admin_call('GET','/admin/resources'),list)
  assert isinstance(admin_call('GET','/admin/payment-attempts'),list)
  assert isinstance(admin_call('GET','/admin/notifications'),list)
  changed_name=StoreSettings.current().business_name+' Runtime Test'
  admin_call('PATCH','/admin/settings',json={'business_name':changed_name})
  public=client.get('http://127.0.0.1:3100/en',timeout=20)
  assert changed_name in public.text
  print('PASS: admin proxy password + TOTP, role/resource contract, reports, operations and runtime brand changes for demo '+args.demo.upper()+'.')
  admin.close();client.close()

 finally:
  for proc,log in processes:
   proc.terminate()
   try:proc.wait(timeout=5)
   except subprocess.TimeoutExpired:proc.kill();proc.wait()
   log.seek(0);errors=[line for line in log.read().splitlines() if 'Error' in line]
   for line in errors:print(line[:300])
   log.close()
  server.shutdown();thread.join(timeout=5);server.server_close()

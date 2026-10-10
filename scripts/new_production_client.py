"""Fresh client backend environment; no database, media, users or payment credentials copied."""
import argparse,base64,re,secrets
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('slug')
parser.add_argument('--domain',required=True)
parser.add_argument('--tls-email',required=True)
parser.add_argument('--image',required=True)
args=parser.parse_args()
if not re.fullmatch(r'[a-z][a-z0-9-]{2,40}',args.slug):parser.error('Invalid client slug.')
if not re.fullmatch(r'[a-z0-9][a-z0-9.-]+\.[a-z]{2,}',args.domain):parser.error('Provide a DNS hostname, without scheme or path.')
if not re.fullmatch(r'[^\s=]+@[^\s=]+\.[^\s=]+',args.tls_email):parser.error('Invalid email.')
if not re.fullmatch(r'[a-zA-Z0-9./:_-]+@sha256:[a-f0-9]{64}',args.image):parser.error('An immutable image digest is required.')
root=Path(__file__).resolve().parents[1]/'client-deployments'/args.slug
root.mkdir(parents=True,mode=0o700,exist_ok=False)
password=secrets.token_urlsafe(40)
config={
    'COMPOSE_PROJECT_NAME':'retail_'+args.slug.replace('-','_'),'RETAIL_IMAGE':args.image,
    'ENVIRONMENT':'production','API_DOMAIN':args.domain,'TLS_EMAIL':args.tls_email,
    'DJANGO_SECRET_KEY':secrets.token_urlsafe(64),
    'FIELD_ENCRYPTION_KEY':base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    'POSTGRES_DB':'retail','POSTGRES_USER':'retail','POSTGRES_PASSWORD':password,
    'DATABASE_URL':f'postgresql://retail:{password}@db:5432/retail?connect_timeout=10',
    'REDIS_URL':'redis://redis:6379/0','ALLOWED_HOSTS':args.domain,
    'CSRF_TRUSTED_ORIGINS':'https://'+args.domain,
    'SESSION_COOKIE_NAME':'retail_'+args.slug.replace('-','_'),'CSRF_COOKIE_NAME':'csrf_'+args.slug.replace('-','_'),
    'CARD_ENABLED':'false','CARD_PROVIDER':'skipcash','SKIPCASH_ENV':'production',
    'SKIPCASH_CLIENT_ID':'','SKIPCASH_KEY_ID':'','SKIPCASH_KEY_SECRET':'','SKIPCASH_WEBHOOK_KEY':'',
    'SKIPCASH_CHECKOUT_HOSTS':'api.skipcash.app,pay.skipcash.app','PAYMENT_RETURN_URL':'',
    'EMAIL_BACKEND':'django.core.mail.backends.smtp.EmailBackend','EMAIL_HOST':'','EMAIL_PORT':'587',
    'EMAIL_HOST_USER':'','EMAIL_HOST_PASSWORD':'','DEFAULT_FROM_EMAIL':'',
    'CUSTOMER_ORIGIN':'','NOTIFICATION_MESSAGE_ID_DOMAIN':args.domain,
    'ANALYTICS_TEST_DEPLOYMENT':'false',
}
path=root/'.env'
with path.open('x') as stream:
    path.chmod(0o600);stream.write('\n'.join(f'{key}={value}' for key,value in config.items())+'\n')
print(f'Created private client-deployments/{args.slug}/.env. Configure merchant and email credentials before launch.')

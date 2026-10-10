"""Create a fresh, private backend-only review environment. Never copies client data."""
import argparse
import secrets
import re
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('slug')
parser.add_argument('--port',type=int,default=8000)
args=parser.parse_args()
if not re.fullmatch(r'[a-z][a-z0-9-]{2,40}',args.slug):parser.error('Use 3–41 lowercase letters, digits or hyphens.')
if not 1024<=args.port<=65535:parser.error('Choose an unprivileged port from 1024 to 65535.')
root=Path(__file__).resolve().parents[1]
directory=root/'client-deployments'/args.slug
directory.mkdir(mode=0o700,parents=True,exist_ok=False)
password=secrets.token_urlsafe(32)
env={
    'COMPOSE_PROJECT_NAME':'retail_'+args.slug.replace('-','_'),
    'RETAIL_RELEASE':'0.3.0-backend','ENVIRONMENT':'development',
    'BACKEND_PORT':str(args.port),'DJANGO_SECRET_KEY':secrets.token_urlsafe(64),
    'POSTGRES_DB':'retail','POSTGRES_USER':'retail','POSTGRES_PASSWORD':password,
    'DATABASE_URL':f'postgresql://retail:{password}@db:5432/retail',
    'REDIS_URL':'redis://redis:6379/0','ALLOWED_HOSTS':'localhost,127.0.0.1,api',
    'CSRF_TRUSTED_ORIGINS':f'http://localhost:{args.port},http://127.0.0.1:{args.port}',
    'EMAIL_BACKEND':'django.core.mail.backends.console.EmailBackend',
    'DEFAULT_FROM_EMAIL':'noreply@localhost',
}
file=directory/'.env'
with file.open('x') as stream:
    file.chmod(0o600)
    stream.write('\n'.join(f'{key}={value}' for key,value in env.items())+'\n')
print(f'Created a private review environment at client-deployments/{args.slug}/.env')
print('No client database, media, users or orders were copied. Configure HTTPS and production settings before launch.')

"""Create a private deployment environment with new secrets. Never copies a DB."""
import argparse,re,secrets
from pathlib import Path
from urllib.parse import quote

p=argparse.ArgumentParser()
p.add_argument('slug');p.add_argument('--storefront-port',type=int,default=8080);p.add_argument('--admin-port',type=int,default=8081)
args=p.parse_args()
if not re.fullmatch('[a-z][a-z0-9-]{2,40}',args.slug):p.error('Use 3–41 lowercase letters, digits and hyphens.')
root=Path(__file__).resolve().parents[1];destination=root/'client-deployments'/args.slug
destination.mkdir(parents=True,exist_ok=False,mode=0o700)
password=secrets.token_urlsafe(32);secret=secrets.token_urlsafe(64)
env=(root/'.env.example').read_text()
env=env.replace('retail_local','retail_'+args.slug.replace('-','_'))
env=env.replace('replace-with-a-unique-random-secret-before-any-shared-deployment',secret)
env=env.replace('replace-with-a-unique-random-database-password',password)
env=env.replace('STOREFRONT_PORT=8080',f'STOREFRONT_PORT={args.storefront_port}').replace('ADMIN_PORT=8081',f'ADMIN_PORT={args.admin_port}')
f=destination/'.env';f.write_text(env);f.chmod(0o600)
print(f'Created {destination}. Secrets are written only to its private .env, not printed.')
print('Use this environment for a fresh deployment. Do not copy another client database or media.')


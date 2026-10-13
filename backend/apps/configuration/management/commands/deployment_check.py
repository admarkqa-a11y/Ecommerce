"""Infrastructure preflight. Does not claim to certify feature-complete V1."""
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.core.cache import cache
from cryptography.fernet import Fernet
from apps.payments.adapters import card_enabled

class Command(BaseCommand):
    help='Fail on missing deployment prerequisites. Run on the actual target environment.'
    def add_arguments(self,parser):parser.add_argument('--require-card',action='store_true')
    def handle(self,*args,**options):
        errors=[]
        if settings.DEBUG:errors.append('Development mode is active.')
        if connection.vendor!='postgresql':errors.append('PostgreSQL is required.')
        try:
            with connection.cursor() as cursor:cursor.execute('SELECT 1')
            executor=MigrationExecutor(connection)
            if executor.migration_plan(executor.loader.graph.leaf_nodes()):errors.append('Unapplied database migrations.')
        except Exception:errors.append('Database/schema unavailable.')
        if not settings.CACHES['default']['BACKEND'].endswith('RedisCache'):errors.append('Shared Redis cache is required.')
        try:
            cache.set('deployment-check','ok',30)
            if cache.get('deployment-check')!='ok':errors.append('Shared cache round trip failed.')
            cache.delete('deployment-check')
        except Exception:errors.append('Redis is unavailable.')
        try:Fernet(settings.FIELD_ENCRYPTION_KEY.encode())
        except Exception:errors.append('Valid field encryption key is required.')
        if options['require_card'] and not card_enabled():errors.append('Configured card adapter is not ready.')
        if settings.EMAIL_BACKEND.endswith(('console.EmailBackend','locmem.EmailBackend')):errors.append('Real email delivery must be configured.')
        if not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL:errors.append('Email host and sender are required.')
        if '*' in settings.ALLOWED_HOSTS:errors.append('Wildcard ALLOWED_HOSTS is forbidden.')
        if errors:raise CommandError('\n'.join(errors))
        self.stdout.write(self.style.SUCCESS('Infrastructure preflight passed. Provider sandbox, full V1 acceptance, restore and load tests remain separate release gates.'))

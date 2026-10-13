import json
from pathlib import Path
from django.core.management.base import BaseCommand
from apps.configuration.models import StoreSettings
from apps.identity.models import Role

class Command(BaseCommand):
    help='Create neutral settings and default client-level roles. Does not create staff or client data.'
    def handle(self,*args,**options):
        StoreSettings.current()
        file=Path(__file__).resolve().parents[5]/'fixtures'/'roles.json'
        for code,capabilities in json.loads(file.read_text()).items():
            Role.objects.get_or_create(code=code,defaults={'name':code.replace('-',' ').title(),'capabilities':capabilities})
        self.stdout.write(self.style.SUCCESS('Neutral configuration and roles are ready.'))


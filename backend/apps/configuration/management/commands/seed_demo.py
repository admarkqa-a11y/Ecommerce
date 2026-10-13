import json
from pathlib import Path
from datetime import time
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from apps.configuration.models import StoreSettings
from apps.identity.models import User
from apps.catalog.models import Brand,Category,Attribute,AttributeOption,Product
from apps.catalog.services import publish
from apps.delivery.models import Zone,Area,Method,Rule
from apps.content.models import Section,Page
from apps.imports.services import upload,confirm

class Command(BaseCommand):
    help='Load synthetic industry configuration into an EMPTY development database. No staff login is seeded.'
    def add_arguments(self,parser):parser.add_argument('client',choices=['a','b'])
    @transaction.atomic
    def handle(self,*args,**options):
        if not settings.DEBUG:raise CommandError('Demo seeding is forbidden outside development.')
        if Product.objects.exists():raise CommandError('Use a separate empty database for each demo.')
        root=Path(__file__).resolve().parents[5]/'fixtures'
        client=options['client'];data=json.loads((root/f'demo-{client}.json').read_text())
        cfg=StoreSettings.current()
        for k,v in data['settings'].items():setattr(cfg,k,v)
        # Synthetic contact numbers are intentionally disabled until replaced by real owner data.
        cfg.whatsapp='';cfg.full_clean();cfg.save()
        brand=data['brand'];Brand.objects.create(code=brand[0],name=brand[1],name_ar=brand[2])
        for code,name,name_ar,parent in data['categories']:
            Category.objects.create(code=code,name=name,name_ar=name_ar,parent=Category.objects.get(code=parent) if parent else None)
        for code,name,name_ar,kind,axis,options_list in data['attrs']:
            attr=Attribute.objects.create(code=code,name=name,name_ar=name_ar,data_type=kind,variant_eligible=axis)
            for option in options_list:AttributeOption.objects.create(attribute=attr,code=option,label=option.replace('-',' ').title(),label_ar=option)
        actor=User(username='demo-importer',email='demo-importer@example.invalid',is_staff=True,is_superuser=True)
        actor.set_unusable_password();actor.save()
        job=upload(actor,SimpleUploadedFile('products.csv',(root/f'products_client_{client}.csv').read_bytes()))
        if job.errors:raise CommandError(str(job.errors))
        confirm(job.id,job.plan_hash,actor)
        for p in Product.objects.all():p.featured=True;p.save();publish(p)
        zone=Zone.objects.create(code='central' if client=='a' else 'service-zone',name='Central zone' if client=='a' else 'Service zone',name_ar='منطقة الخدمة')
        area=Area.objects.create(zone=zone,code='central-area' if client=='a' else 'trade-area',name='Central area' if client=='a' else 'Trade area',name_ar='منطقة التوصيل')
        for code,name,name_ar,fee,cutoff in [('standard','Standard delivery','توصيل عادي',data['delivery_fee'],None),('express','Express delivery','توصيل سريع','35',time(16)),('same_day','Same-day delivery','توصيل في نفس اليوم','45',time(12)),('pickup','Store pickup','الاستلام من المتجر','0',None)]:
            method=Method.objects.create(code=code,name=name,name_ar=name_ar,kind=code,weekdays=[0,1,2,3,4,5,6],cutoff=cutoff,pickup_address='Set your pickup address' if code=='pickup' else '')
            if code!='pickup':Rule.objects.create(method=method,area=area,fee=fee,free_threshold=data['free_threshold'])
        hero=Section.objects.create(kind='hero',**data['hero']);hero.publication={k:getattr(hero,k) for k in ['kind','title','title_ar','body','body_ar','properties']};hero.save()
        for section_data in data.get('sections', []):
            section=Section.objects.create(**section_data)
            section.publication={k:getattr(section,k) for k in ['kind','title','title_ar','body','body_ar','properties']}
            section.save()
        featured=Section.objects.create(kind='featured_products',title='Selected for you',title_ar='اخترنا لك',position=10)
        featured.publication={k:getattr(featured,k) for k in ['kind','title','title_ar','body','body_ar','properties']};featured.save()
        for slug,title,title_ar in [('about','About us','من نحن'),('contact','Contact','تواصل معنا'),('privacy','Privacy policy','سياسة الخصوصية'),('terms','Terms and conditions','الشروط والأحكام'),('shipping','Shipping policy','سياسة الشحن'),('returns','Return and refund policy','سياسة الاسترجاع والاسترداد'),('warranty','Warranty policy','سياسة الضمان')]:
            page=Page.objects.create(slug=slug,title=title,title_ar=title_ar,body='Add your approved business content before launch.',body_ar='أضف محتوى نشاطك التجاري المعتمد قبل الإطلاق.')
            # Policy drafts are not published automatically.
        actor.is_active=False;actor.save()
        self.stdout.write(self.style.SUCCESS(f'Demo {client.upper()} loaded. Create an admin separately. Policy pages and contact details need your configuration.'))


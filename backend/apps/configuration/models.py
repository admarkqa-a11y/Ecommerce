from django.db import models
from django.core.exceptions import ValidationError
from common.models import Entity

class StoreSettings(Entity):
    singleton = models.PositiveSmallIntegerField(default=1, unique=True, editable=False)
    business_name = models.CharField(max_length=200, default='Your store')
    business_name_ar = models.CharField(max_length=200, blank=True)
    tagline = models.CharField(max_length=250, blank=True)
    tagline_ar = models.CharField(max_length=250, blank=True)
    logo_url = models.CharField(max_length=500, blank=True)
    favicon_url = models.CharField(max_length=500, blank=True)
    primary_color = models.CharField(max_length=7, default='#1C5948')
    accent_color = models.CharField(max_length=7, default='#DCECC5')
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    currency = models.CharField(max_length=3, default='QAR')
    currency_exponent = models.PositiveSmallIntegerField(default=2)
    timezone = models.CharField(max_length=64, default='Asia/Qatar')
    languages = models.JSONField(default=list, blank=True)
    social_links = models.JSONField(default=dict, blank=True)
    bank_instructions = models.TextField(blank=True)
    cod_enabled = models.BooleanField(default=True)
    bank_enabled = models.BooleanField(default=False)
    revision = models.PositiveIntegerField(default=1)

    def clean(self):
        import re
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        if self.singleton != 1:
            raise ValidationError('Only one settings record per deployment is allowed.')
        for color in [self.primary_color, self.accent_color]:
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
                raise ValidationError('Colors must be six-digit hex values.')
        if self.whatsapp and not re.fullmatch(r'[1-9][0-9]{6,14}', self.whatsapp):
            raise ValidationError('WhatsApp requires international digits without + or spaces.')
        try: ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError: raise ValidationError('Invalid IANA timezone.')
        if not re.fullmatch('[A-Z]{3}', self.currency) or self.currency_exponent > 4:
            raise ValidationError('Invalid currency configuration.')
        if self.pk and StoreSettings.objects.filter(pk=self.pk).exists():
            old = StoreSettings.objects.get(pk=self.pk)
            if (old.currency, old.currency_exponent) != (self.currency, self.currency_exponent):
                from apps.orders.models import Order
                if Order.objects.exists(): raise ValidationError('Currency is locked after the first order. Use a controlled migration.')

    @classmethod
    def current(cls):
        return cls.objects.get_or_create(singleton=1, defaults={'languages':['en','ar']})[0]


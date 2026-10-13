from django.db import models
from common.models import Entity
from django.core.exceptions import ValidationError
from decimal import Decimal

PRIORITIES={'bundle':800,'bxgy':700,'flash':600,'deal':500,'product':400,'category':300,'brand':200,'coupon':100}

class Promotion(Entity):
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20,choices=[(x,x) for x in ['product','category','brand','flash','deal','coupon','bundle','bxgy']])
    priority = models.PositiveIntegerField(default=400)
    enabled = models.BooleanField(default=False)
    starts_at = models.DateTimeField(null=True,blank=True)
    ends_at = models.DateTimeField(null=True,blank=True)
    coupon_code = models.CharField(max_length=50,blank=True)
    discount_type = models.CharField(max_length=12,choices=[('percent','Percentage'),('fixed','Fixed')],default='percent')
    value = models.DecimalField(max_digits=20,decimal_places=6,default=0)
    minimum = models.DecimalField(max_digits=20,decimal_places=6,default=0)
    maximum = models.DecimalField(max_digits=20,decimal_places=6,null=True,blank=True)
    products = models.ManyToManyField('catalog.Product',blank=True)
    categories = models.ManyToManyField('catalog.Category',blank=True)
    brands = models.ManyToManyField('catalog.Brand',blank=True)
    global_limit = models.PositiveIntegerField(null=True,blank=True)
    used = models.PositiveIntegerField(default=0)
    held = models.PositiveIntegerField(default=0)
    rules = models.JSONField(default=dict,blank=True)
    per_customer_limit = models.PositiveIntegerField(null=True,blank=True)
    customers = models.ManyToManyField('identity.User',blank=True)

    def clean(self):
        if not 1<=self.priority<=999:raise ValidationError('Priority must be between 1 and 999.')
        if self.value<0 or (self.discount_type=='percent' and self.value>100):raise ValidationError('Invalid discount value.')
        if self.minimum<0 or (self.maximum is not None and self.maximum<0):raise ValidationError('Invalid promotion bounds.')
        if self.starts_at and self.ends_at and self.ends_at<=self.starts_at:raise ValidationError('Promotion end must follow start.')
        if self.kind=='coupon' and not self.coupon_code:raise ValidationError('Coupon code required.')
        if not isinstance(self.rules,dict):raise ValidationError('Rules must be an object.')
        if self.kind=='bundle':
            from apps.catalog.models import Variant
            components=self.rules.get('components',{})
            if not isinstance(components,dict) or not components or len(components)>20:raise ValidationError('A bundle needs 1–20 fixed variant components.')
            if any(isinstance(q,bool) or not isinstance(q,int) or not 1<=q<=50 for q in components.values()):raise ValidationError('Bundle quantities must be integers from 1 to 50.')
            if Variant.objects.filter(pk__in=components).count()!=len(components):raise ValidationError('Unknown bundle variant.')
            try:price=Decimal(str(self.rules['price']))
            except Exception:raise ValidationError('Bundle price required.')
            if not price.is_finite() or price<0:raise ValidationError('Invalid bundle price.')
        if self.kind=='bxgy':
            for key in ['buy','get','max_applications']:
                value=self.rules.get(key,1)
                if isinstance(value,bool) or not isinstance(value,int) or not 1<=value<=200:raise ValidationError('BXGY quantities must be integers from 1 to 200.')
            if self.discount_type!='percent':raise ValidationError('BXGY uses a percentage reward.')
            for key in ['qualifier_scope','reward_scope']:
                scope=self.rules.get(key,{})
                if not isinstance(scope,dict) or set(scope)-{'products','variants','categories','brands'}:raise ValidationError('Invalid BXGY scope.')
                from uuid import UUID
                for values in scope.values():
                    if not isinstance(values,list):raise ValidationError('Scope IDs must be lists.')
                    try:
                        for value in values:UUID(str(value))
                    except ValueError:raise ValidationError('Scope IDs must be UUIDs.')

class Redemption(Entity):
    promotion = models.ForeignKey(Promotion,related_name='redemptions',on_delete=models.PROTECT)
    order = models.ForeignKey('orders.Order',on_delete=models.PROTECT)
    customer = models.ForeignKey('identity.User',null=True,on_delete=models.PROTECT)
    state = models.CharField(max_length=12,default='held')
    class Meta:
        constraints=[models.UniqueConstraint(fields=['promotion','order'],name='promotion_order_once')]

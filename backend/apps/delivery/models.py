from django.db import models
from common.models import Entity
from django.core.exceptions import ValidationError

class Zone(Entity):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120,blank=True)

class Area(Entity):
    zone = models.ForeignKey(Zone,on_delete=models.PROTECT)
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120,blank=True)

class Method(Entity):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    name_ar = models.CharField(max_length=120,blank=True)
    kind = models.CharField(max_length=20,choices=[(x,x) for x in ['standard','express','same_day','pickup']])
    enabled = models.BooleanField(default=True)
    cutoff = models.TimeField(null=True,blank=True)
    weekdays = models.JSONField(default=list, blank=True)
    blackout_dates = models.JSONField(default=list, blank=True)
    pickup_address = models.TextField(blank=True)
    def clean(self):
        from datetime import date
        if not isinstance(self.weekdays,list) or any(isinstance(d,bool) or not isinstance(d,int) or d not in range(7) for d in self.weekdays):
            raise ValidationError('Weekdays must be integers 0 (Monday) to 6 (Sunday).')
        try:
            if not isinstance(self.blackout_dates,list):raise ValueError()
            for value in self.blackout_dates:date.fromisoformat(value)
        except (ValueError,TypeError):raise ValidationError('Blackout dates must be ISO dates.')

class Rule(Entity):
    method = models.ForeignKey(Method,related_name='rules',on_delete=models.CASCADE)
    area = models.ForeignKey(Area,on_delete=models.PROTECT,null=True,blank=True)
    zone = models.ForeignKey(Zone,on_delete=models.PROTECT,null=True,blank=True)
    minimum = models.DecimalField(max_digits=20,decimal_places=6,default=0)
    fee = models.DecimalField(max_digits=20,decimal_places=6,default=0)
    free_threshold = models.DecimalField(max_digits=20,decimal_places=6,null=True,blank=True)
    upper_bound = models.DecimalField(max_digits=20,decimal_places=6,null=True,blank=True)
    def clean(self):
        if self.minimum<0 or self.fee<0 or (self.free_threshold is not None and self.free_threshold<0):raise ValidationError('Delivery amounts must be nonnegative.')
        if self.upper_bound is not None and self.upper_bound<=self.minimum:raise ValidationError('Delivery upper bound must exceed minimum.')
        peers=Rule.objects.filter(method_id=self.method_id,area_id=self.area_id,zone_id=self.zone_id).exclude(pk=self.pk)
        for peer in peers:
            if (self.upper_bound is None or peer.minimum<self.upper_bound) and (peer.upper_bound is None or self.minimum<peer.upper_bound):
                raise ValidationError('Delivery value bands must not overlap for the same target.')
    class Meta:
        constraints=[models.CheckConstraint(condition=models.Q(area__isnull=True)|models.Q(zone__isnull=True),name='delivery_one_target')]

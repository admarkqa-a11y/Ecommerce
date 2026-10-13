from django.db import models
from django.db.models import F,Q
from common.models import Entity

class Balance(Entity):
    variant = models.OneToOneField('catalog.Variant',related_name='inventory',on_delete=models.PROTECT)
    on_hand = models.PositiveIntegerField(default=0)
    reserved = models.PositiveIntegerField(default=0)
    committed = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    @property
    def available(self): return self.on_hand-self.reserved-self.committed
    class Meta:
        constraints=[models.CheckConstraint(condition=Q(on_hand__gte=F('reserved')+F('committed')),name='stock_covers_allocations')]

class Movement(Entity):
    variant = models.ForeignKey('catalog.Variant',on_delete=models.PROTECT)
    operation_key = models.CharField(max_length=250,unique=True)
    on_hand_delta = models.IntegerField(default=0)
    reserved_delta = models.IntegerField(default=0)
    committed_delta = models.IntegerField(default=0)
    reason = models.TextField()
    actor = models.ForeignKey('identity.User',on_delete=models.PROTECT,null=True)


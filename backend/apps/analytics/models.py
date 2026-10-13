from django.db import models
from common.models import Entity

class ShoppingSession(Entity):
    last_seen = models.DateTimeField()
    qualified = models.BooleanField(default=False)
    locale = models.CharField(max_length=8,default='en')

class Event(Entity):
    key = models.CharField(max_length=220,unique=True)
    kind = models.CharField(max_length=40)
    session_key = models.CharField(max_length=64,blank=True)
    order = models.ForeignKey('orders.Order',on_delete=models.PROTECT,null=True)
    data = models.JSONField(default=dict, blank=True)
    shopping_session = models.ForeignKey(ShoppingSession,null=True,on_delete=models.SET_NULL)
    schema_version = models.PositiveSmallIntegerField(default=1)
    source = models.CharField(max_length=12,default='server')

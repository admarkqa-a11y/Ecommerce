from django.db import models
from common.models import Entity

class Capture(Entity):
    order = models.ForeignKey('orders.Order',related_name='captures',on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=20,decimal_places=6)
    reference = models.CharField(max_length=200)
    operation_key = models.CharField(max_length=250,unique=True)
    actor = models.ForeignKey('identity.User',on_delete=models.PROTECT,null=True)

class Refund(Entity):
    order = models.ForeignKey('orders.Order',related_name='refunds',on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=20,decimal_places=6)
    state = models.CharField(max_length=20,default='pending')
    reason = models.TextField()
    reference = models.CharField(max_length=200,blank=True)
    operation_key = models.CharField(max_length=250,unique=True)
    actor = models.ForeignKey('identity.User',on_delete=models.PROTECT)
    allocations = models.JSONField(default=dict, blank=True)
    succeeded_at = models.DateTimeField(null=True)

class PaymentAttempt(Entity):
    order = models.OneToOneField('orders.Order',related_name='card_attempt',on_delete=models.PROTECT)
    provider = models.CharField(max_length=30)
    state = models.CharField(max_length=30,default='created')
    reference = models.CharField(max_length=200,blank=True)
    checkout_url = models.URLField(max_length=1000,blank=True)
    last_checked_at = models.DateTimeField(null=True)
    issue = models.CharField(max_length=100,blank=True)

class WebhookReceipt(Entity):
    digest = models.CharField(max_length=64,unique=True)
    attempt = models.ForeignKey(PaymentAttempt,on_delete=models.PROTECT)
    processed_at = models.DateTimeField(null=True)

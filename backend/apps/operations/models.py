from django.db import models
from common.models import Entity

class Audit(Entity):
    actor = models.ForeignKey('identity.User',on_delete=models.PROTECT,null=True)
    action = models.CharField(max_length=100)
    resource = models.CharField(max_length=100)
    reason = models.TextField(blank=True)

class Outbox(Entity):
    key = models.CharField(max_length=220,unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    delivered_at = models.DateTimeField(null=True)
    attempts = models.PositiveIntegerField(default=0)
    claimed_at = models.DateTimeField(null=True)
    retry_at = models.DateTimeField(null=True)
    last_error = models.CharField(max_length=100,blank=True)

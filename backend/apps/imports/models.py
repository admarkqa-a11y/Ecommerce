from django.db import models
from common.models import Entity

class ImportJob(Entity):
    actor = models.ForeignKey('identity.User',on_delete=models.PROTECT)
    mode = models.CharField(max_length=10,default='create')
    state = models.CharField(max_length=20,default='uploaded')
    rows = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    plan_hash = models.CharField(max_length=64,blank=True)
    stock_mode = models.CharField(max_length=25,default='preserve_existing')
    dependency_hash = models.CharField(max_length=64,blank=True)
    result = models.JSONField(default=dict, blank=True)


import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from common.models import Entity

class Role(Entity):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    capabilities = models.JSONField(default=list, blank=True)

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    locale = models.CharField(max_length=8, default='en')
    email_verified = models.BooleanField(default=False)
    roles = models.ManyToManyField(Role, blank=True)
    mfa_secret = models.TextField(blank=True)
    mfa_last_counter = models.BigIntegerField(default=-1)

    def can(self, capability):
        return self.is_active and self.is_staff and (self.is_superuser or any(
            capability in r.capabilities for r in self.roles.all()))

class EmailChallenge(Entity):
    email = models.EmailField()
    digest = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempts = models.PositiveIntegerField(default=0)
    consumed = models.BooleanField(default=False)


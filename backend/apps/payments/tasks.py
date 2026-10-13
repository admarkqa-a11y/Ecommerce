from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import PaymentAttempt
from .card import reconcile
from .adapters import ProviderUnavailable,InvalidProviderResponse
from common.api import Conflict

@shared_task
def reconcile_pending_payments():
    for attempt in PaymentAttempt.objects.filter(state__in=['creating','pending','unknown'],updated_at__lt=timezone.now()-timedelta(minutes=1)).iterator():
        try:reconcile(attempt.id)
        except (ProviderUnavailable,InvalidProviderResponse,Conflict):continue

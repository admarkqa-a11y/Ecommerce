from celery import shared_task
from django.utils import timezone
from .models import Order
from .services import transition
from common.api import Conflict

@shared_task
def expire_orders():
    for order in Order.objects.filter(state='pending',expires_at__lte=timezone.now()).iterator():
        try:transition(order.id,'cancel',reason='Payment reservation expired',only_if_expired=True)
        except Conflict:continue  # Unknown/in-flight card payments keep their reservation until reconciled.

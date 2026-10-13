"""At-least-once email delivery with a durable claim and bounded retries.

SMTP cannot guarantee exactly-once delivery across a crash after acceptance.
Stable Message-ID makes duplicate diagnosis possible without storing email bodies.
"""
from datetime import timedelta
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Outbox

LABELS={
    'order.accepted':('Order confirmed','تم تأكيد الطلب'),
    'order.cancelled':('Order cancelled','تم إلغاء الطلب'),
    'order.shipped':('Order shipped','تم شحن الطلب'),
    'order.delivered':('Order delivered','تم توصيل الطلب'),
    'order.collected':('Order collected','تم استلام الطلب'),
    'refund.succeeded':('Refund recorded','تم تسجيل الاسترداد'),
}

def send_event(event):
    from apps.orders.models import Order
    if event.event_type not in LABELS:raise ValueError('unsupported_notification_type')
    order=Order.objects.get(pk=event.payload['order_id'])
    title,arabic=LABELS[event.event_type]
    body=(f'{order.business_snapshot.get("name","")}\n{title} / {arabic}\n'
          f'Order / الطلب: {order.number}\nTotal / الإجمالي: {order.total} {order.currency}\n')
    if event.event_type=='refund.succeeded':
        from apps.payments.models import Refund
        refund=Refund.objects.get(pk=event.payload['refund_id'],order=order,state='succeeded')
        body+=f'Refund amount / مبلغ الاسترداد: {refund.amount} {order.currency}\n'
    # Both values originate in a validated order snapshot. No credentials or tokens.
    message=EmailMessage(f'{title} — {order.number}',body,settings.DEFAULT_FROM_EMAIL,[order.contact['email']],
        headers={'Message-ID':f'<retail-{event.id}@{settings.NOTIFICATION_MESSAGE_ID_DOMAIN}>'})
    if message.send(fail_silently=False)!=1:raise RuntimeError('email_not_accepted')

@shared_task
def deliver_outbox(limit=50):
    delivered=0
    for _ in range(min(max(int(limit),1),100)):
        now=timezone.now()
        with transaction.atomic():
            event=(Outbox.objects.select_for_update(skip_locked=True).filter(delivered_at__isnull=True,attempts__lt=8)
                .filter(Q(retry_at__isnull=True)|Q(retry_at__lte=now))
                .filter(Q(claimed_at__isnull=True)|Q(claimed_at__lt=now-timedelta(minutes=10)))
                .order_by('created_at').first())
            if event is None:break
            event.claimed_at=now;event.attempts+=1;event.save()
        try:send_event(event)
        except Exception:
            # Never persist exception text: SMTP failures may include credentials.
            Outbox.objects.filter(pk=event.id).update(claimed_at=None,last_error='delivery_failed',
                retry_at=timezone.now()+timedelta(minutes=min(1440,2**event.attempts)))
        else:
            Outbox.objects.filter(pk=event.id).update(delivered_at=timezone.now(),claimed_at=None,retry_at=None,last_error='')
            delivered+=1
    return delivered

"""Consent-based session analytics. Financial records, never browser values, drive reports."""
from collections import defaultdict
from datetime import datetime, timedelta, time, date
from decimal import Decimal
from zoneinfo import ZoneInfo
import re
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, F
from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import ValidationError
from .models import ShoppingSession, Event

DEFINITION='Unique accepted purchases attributed within seven days / qualified shopping sessions × 100. Cohort: session start date; idle timeout: 30 minutes. Multiple purchases per session can exceed 100%.'

def eligible_request(request):
    return (not getattr(request.user,'is_staff',False)
        and not getattr(settings,'ANALYTICS_TEST_DEPLOYMENT',False)
        and not re.search(r'bot|spider|crawler|headless',request.headers.get('User-Agent',''),re.I))

@transaction.atomic
def shopping_session(request):
    if request.session.get('analytics_consent') is not True or not eligible_request(request):return None
    now=timezone.now()
    current=ShoppingSession.objects.select_for_update().filter(pk=request.session.get('shopping_session_id')).first() if request.session.get('shopping_session_id') else None
    if current is None or now-current.last_seen>=timedelta(minutes=30):
        current=ShoppingSession.objects.create(last_seen=now,locale=request.session.get('locale','en'))
        request.session['shopping_session_id']=str(current.id)
    else:
        current.last_seen=now;current.save(update_fields=['last_seen'])
    return current

def track(request,kind,key,data):
    session=shopping_session(request)
    if session is None:return None
    event,_=Event.objects.get_or_create(key=f'{session.id}:{key}',defaults={
        'kind':kind,'shopping_session':session,'source':'browser' if kind=='product_view' else 'server','data':data})
    if not session.qualified:
        session.qualified=True;session.save(update_fields=['qualified'])
    return event

def period(params):
    from apps.configuration.models import StoreSettings
    zone=ZoneInfo(StoreSettings.current().timezone)
    today=timezone.now().astimezone(zone).date()
    try:
        first=date.fromisoformat(params.get('from',str(today-timedelta(days=29))))
        last=date.fromisoformat(params.get('to',str(today)))
    except (ValueError,TypeError):raise ValidationError('Dates must be YYYY-MM-DD.')
    if last<first or (last-first).days>365:raise ValidationError('Select an ordered date range of at most 366 days.')
    return datetime.combine(first,time.min,zone),datetime.combine(last+timedelta(days=1),time.min,zone),zone

def dashboard(params):
    from apps.orders.models import Order, OrderItem
    from apps.payments.models import Capture, Refund
    from apps.inventory.models import Balance
    from apps.catalog.models import Product
    from apps.identity.models import User
    start,end,zone=period(params)
    accepted=Order.objects.filter(accepted_at__gte=start,accepted_at__lt=end)
    cancelled=Order.objects.filter(accepted_at__isnull=False,cancelled_at__gte=start,cancelled_at__lt=end,departed_at__isnull=True)
    dates=defaultdict(lambda:Decimal(0));categories={};brands={};best={}
    sales=Decimal(0)
    for qs,sign,clock in [(accepted,1,'accepted_at'),(cancelled,-1,'cancelled_at')]:
        for item in OrderItem.objects.filter(order__in=qs).select_related('order').iterator(chunk_size=500):
            value=item.net*sign;sales+=value
            day=getattr(item.order,clock).astimezone(zone).date().isoformat();dates[day]+=value
            for target,field in [(categories,'category'),(brands,'brand')]:
                snapshot=item.snapshot.get(field) or {'id':'unbranded','name':'Unbranded','name_ar':'بدون علامة تجارية'}
                key=str(snapshot['id'])
                record=target.setdefault(key,{'id':key,'name':snapshot.get('name',''),'name_ar':snapshot.get('name_ar',''),'sales':Decimal(0)})
                record['sales']+=value
            sku=item.snapshot['sku']
            record=best.setdefault(sku,{'sku':sku,'name':item.snapshot['name'],'quantity':0,'sales':Decimal(0)})
            record['quantity']+=item.quantity*sign;record['sales']+=value
    captured=Capture.objects.filter(created_at__gte=start,created_at__lt=end).aggregate(n=Sum('amount'))['n'] or Decimal(0)
    refunded=Refund.objects.filter(state='succeeded',succeeded_at__gte=start,succeeded_at__lt=end).aggregate(n=Sum('amount'))['n'] or Decimal(0)
    qualified=ShoppingSession.objects.filter(qualified=True,created_at__gte=start,created_at__lt=end)
    denominator=qualified.count()
    attributed=Order.objects.filter(shopping_session__in=qualified,accepted_at__isnull=False,
        accepted_at__gte=F('shopping_session__created_at'),accepted_at__lt=F('shopping_session__created_at')+timedelta(days=7)).count()
    # Verified account email mapping prevents counting linked guest identities twice.
    verified={u.email.lower():str(u.id) for u in User.objects.filter(email_verified=True).only('id','email')}
    identities=set()
    for owner,contact in accepted.values_list('owner_id','contact').iterator():
        email=str(contact.get('email','')).strip().lower()
        identities.add(str(owner) if owner else verified.get(email) or salted_hmac('report-identity',email).hexdigest())
    balances=Balance.objects.filter(variant__active=True,variant__product__status='active').annotate(
        available_now=F('on_hand')-F('reserved')-F('committed')).filter(available_now__lte=F('variant__product__threshold')).select_related('variant')
    low=[{'variant_id':str(b.variant_id),'sku':b.variant.sku,'available':b.available_now,'out_of_stock':b.available_now==0} for b in balances]
    def amounts(records):return [dict(r,sales=str(r['sales'])) for r in records]
    order_count=accepted.count()
    covered=accepted.filter(shopping_session__qualified=True,accepted_at__gte=F('shopping_session__created_at'),
        accepted_at__lt=F('shopping_session__created_at')+timedelta(days=7)).count()
    return {'from':start.date().isoformat(),'to':(end.date()-timedelta(days=1)).isoformat(),'timezone':str(zone),
        'orders':order_count,'cancelled_orders':cancelled.count(),'sales':str(sales),'captured':str(captured),
        'refunds':str(refunded),'revenue':str(captured-refunded),'customers':len(identities),
        'registered_customers':User.objects.filter(is_staff=False,date_joined__gte=start,date_joined__lt=end).count(),
        'products':Product.objects.filter(status='active').count(),'low_stock':len(low),'low_stock_items':low,
        'sales_by_date':[{'date':day,'sales':str(value)} for day,value in sorted(dates.items())],
        'sales_by_category':amounts(sorted(categories.values(),key=lambda r:r['id'])),
        'sales_by_brand':amounts(sorted(brands.values(),key=lambda r:r['id'])),
        'best_selling_products':amounts(sorted(best.values(),key=lambda r:(-r['quantity'],r['sku']))[:20]),
        'qualified_sessions':denominator,'attributed_purchases':attributed,
        'conversion':str(Decimal(attributed)*100/denominator) if denominator else None,
        'conversion_definition':DEFINITION,'conversion_provisional':timezone.now()<end+timedelta(days=7),
        'attribution_coverage':str(Decimal(covered)*100/order_count) if order_count else None,
        'unattributed_orders':order_count-covered,
        'outside_window_orders':accepted.filter(shopping_session__isnull=False,accepted_at__gte=F('shopping_session__created_at')+timedelta(days=7)).count()}

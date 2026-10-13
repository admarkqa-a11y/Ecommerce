from decimal import Decimal
from zoneinfo import ZoneInfo
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.configuration.models import StoreSettings
from .models import Area,Method

def quote_delivery(method_id,area_id,net,now=None):
    try: method=Method.objects.get(pk=method_id,enabled=True)
    except (Method.DoesNotExist,ValueError): raise ValidationError('Delivery method is unavailable.')
    local=(now or timezone.now()).astimezone(ZoneInfo(StoreSettings.current().timezone))
    if method.weekdays and local.weekday() not in method.weekdays: raise ValidationError('Delivery is unavailable on this day.')
    if local.date().isoformat() in method.blackout_dates: raise ValidationError('Delivery is unavailable on this date.')
    if method.kind in ['same_day','express'] and method.cutoff and local.time().replace(tzinfo=None)>=method.cutoff:
        raise ValidationError('The cutoff time for this delivery method has passed.')
    if method.kind=='pickup':return method,Decimal(0)
    try: area=Area.objects.get(pk=area_id)
    except (Area.DoesNotExist,ValueError): raise ValidationError('Choose a valid delivery area.')
    rules=list(method.rules.all())
    specific=[r for r in rules if r.area_id==area.id]
    zone=[r for r in rules if r.area_id is None and r.zone_id==area.zone_id]
    fallback=[r for r in rules if r.area_id is None and r.zone_id is None]
    matches=specific or zone or fallback
    matches=[r for r in matches if net>=r.minimum and (r.upper_bound is None or net<r.upper_bound)]
    if len(matches)!=1:raise ValidationError('This area has no unambiguous delivery rule.')
    rule=matches[0]
    if net<rule.minimum:raise ValidationError(f'Minimum merchandise amount: {rule.minimum}.')
    return method,Decimal(0) if rule.free_threshold is not None and net>=rule.free_threshold else rule.fee

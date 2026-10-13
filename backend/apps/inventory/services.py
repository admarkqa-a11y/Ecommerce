from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Balance,Movement

@transaction.atomic
def move(variant_id,key,reason,on_hand=0,reserved=0,committed=0,actor=None):
    balance=Balance.objects.select_for_update().get(variant_id=variant_id)
    old=Movement.objects.filter(operation_key=key).first()
    if old:
        if (old.variant_id,old.on_hand_delta,old.reserved_delta,old.committed_delta)!=(balance.variant_id,on_hand,reserved,committed):
            raise ValidationError('Idempotency key was used for a different inventory operation.')
        return balance
    if any(isinstance(v,bool) or not isinstance(v,int) for v in [on_hand,reserved,committed]): raise ValidationError('Stock must use whole units.')
    balance.on_hand+=on_hand;balance.reserved+=reserved;balance.committed+=committed
    if min(balance.on_hand,balance.reserved,balance.committed,balance.available)<0:
        raise ValidationError('Insufficient available stock or invalid stock adjustment.')
    balance.version+=1;balance.save()
    Movement.objects.create(variant_id=variant_id,operation_key=key,reason=reason,
        on_hand_delta=on_hand,reserved_delta=reserved,committed_delta=committed,actor=actor)
    return balance

def adjust(variant_id,delta,reason,key,actor=None):
    if not isinstance(reason,str) or not reason.strip():raise ValidationError('An adjustment reason is required.')
    if not isinstance(key,str) or not 1<=len(key)<=250:raise ValidationError('A valid idempotency key is required.')
    return move(variant_id,key,reason,on_hand=delta,actor=actor)

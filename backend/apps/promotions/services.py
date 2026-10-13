from decimal import Decimal
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from common.money import money,allocate
from .models import Promotion

def matches(promo,product):
    ids=list(promo.products.values_list('id',flat=True));brands=list(promo.brands.values_list('id',flat=True));cats=list(promo.categories.values_list('id',flat=True))
    if not ids and not brands and not cats:return True
    node=product.category;ancestors=[]
    while node:ancestors.append(node.pk);node=node.parent
    return product.pk in ids or product.brand_id in brands or bool(set(cats)&set(ancestors))

def scope_matches(scope,unit,promo):
    if not scope:return matches(promo,unit['product'])
    product=unit['product'];node=product.category;ancestors=[]
    while node:ancestors.append(str(node.pk));node=node.parent
    return (str(product.pk) in scope.get('products',[]) or str(unit['variant'].pk) in scope.get('variants',[])
        or str(product.brand_id) in scope.get('brands',[]) or bool(set(ancestors)&set(scope.get('categories',[]))))

def customer_eligible(promo,customer):
    targets=list(promo.customers.values_list('id',flat=True))
    if (targets or promo.per_customer_limit is not None) and customer is None:return False
    if targets and customer.pk not in targets:return False
    return promo.per_customer_limit is None or promo.redemptions.filter(customer=customer,state__in=['held','used']).count()<promo.per_customer_limit

def calculate(lines,coupon='',exponent=2,customer=None,return_details=False):
    """Unit allocation; a discounted unit cannot receive a coupon as well."""
    units=[]
    for line_idx,line in enumerate(lines):
        for _ in range(line['quantity']):
            units.append({'line':line_idx,'product':line['variant'].product,'variant':line['variant'],
                          'price':money(line['price'],exponent),'discount':Decimal(0),'promotion':None,'used':False,
                          'bundle':line.get('bundle_group'),'bundle_promotion':line.get('bundle_promotion')})
    now=timezone.now()
    promos=list(Promotion.objects.filter(enabled=True).filter(Q(starts_at__isnull=True)|Q(starts_at__lte=now)).filter(Q(ends_at__isnull=True)|Q(ends_at__gt=now)).prefetch_related('products','categories','brands'))
    candidates=[];trace=[]
    for i,u in enumerate(units):
        sale=lines[u['line']].get('sale_price')
        if sale is not None and money(sale,exponent)<u['price']:
            candidates.append((350,u['price']-money(sale,exponent),'sale:'+str(i),[i],{i:u['price']-money(sale,exponent)},None))
    for p in promos:
        if p.kind=='coupon' or (p.global_limit is not None and p.used+p.held>=p.global_limit):continue
        if not customer_eligible(p,customer):continue
        eligible=[i for i,u in enumerate(units) if matches(p,u['product'])]
        subtotal=sum((units[i]['price'] for i in eligible),Decimal(0))
        if subtotal<p.minimum:continue
        if p.kind=='bundle':
            groups=sorted({u['bundle'] for u in units if u['bundle'] and u['bundle_promotion']==str(p.id)})
            for group in groups:
                selected=[i for i,u in enumerate(units) if u['bundle']==group]
                actual={}
                for i in selected:
                    key=str(units[i]['variant'].pk);actual[key]=actual.get(key,0)+1
                if actual!=p.rules.get('components'):raise ValidationError('Bundle components changed. Add the bundle again.')
                gross=sum((units[i]['price'] for i in selected),Decimal(0))
                price=money(p.rules['price'],exponent)
                if price>gross:raise ValidationError('Bundle price exceeds its component total.')
                shares=allocate(gross-price,[units[i]['price'] for i in selected],exponent)
                candidates.append((p.priority,gross-price,str(p.id)+group,selected,dict(zip(selected,shares)),p))
            continue
        if p.kind=='bxgy':
            x=int(p.rules.get('buy',0));y=int(p.rules.get('get',0));applications=int(p.rules.get('max_applications',1))
            if x<1 or y<1 or applications<1:continue
            pool=set(range(len(units)))
            for repeat in range(applications):
                rewards=sorted([i for i in pool if scope_matches(p.rules.get('reward_scope'),units[i],p)],key=lambda i:(units[i]['price'],units[i]['variant'].sku,i))
                qualifiers=[i for i in pool if scope_matches(p.rules.get('qualifier_scope'),units[i],p)]
                reward=[]
                for i in rewards:
                    candidate=reward+[i]
                    if len(set(qualifiers)-set(candidate))>=x:reward=candidate
                    if len(reward)==y:break
                if len(reward)<y:break
                qualifiers=sorted(set(qualifiers)-set(reward),key=lambda i:(units[i]['variant'].sku,i))[:x]
                consumed=reward+qualifiers
                reward_total=sum((units[i]['price'] for i in reward),Decimal(0))*min(p.value,Decimal(100))/100
                shares=allocate(reward_total,[units[i]['price'] for i in reward],exponent)
                discounts=dict(zip(reward,shares))
                candidates.append((p.priority,sum(discounts.values()),str(p.id)+str(repeat),consumed,discounts,p))
                pool-=set(consumed)
        else:
            amount=subtotal*p.value/100 if p.discount_type=='percent' else p.value
            amount=min(subtotal,amount,p.maximum if p.maximum is not None else subtotal)
            shares=allocate(amount,[units[i]['price'] for i in eligible],exponent)
            for i,share in zip(eligible,shares):
                candidates.append((p.priority,share,str(p.id)+str(i),[i],{i:share},p))
    for priority,saving,key,consumed,discounts,p in sorted(candidates,key=lambda c:(-c[0],-c[1],c[2])):
        if any(units[i]['used'] for i in consumed):
            trace.append({'candidate':key,'priority':priority,'saving':str(saving),'selected':False,'reason':'units_already_allocated'});continue
        trace.append({'candidate':key,'priority':priority,'saving':str(saving),'selected':True})
        for i in consumed:
            units[i]['used']=True;units[i]['promotion']=p
            units[i]['discount']=min(units[i]['price'],discounts.get(i,Decimal(0)))
    if coupon:
        p=next((p for p in promos if p.kind=='coupon' and p.coupon_code.upper()==coupon.strip().upper()),None)
        if not p or not customer_eligible(p,customer) or (p.global_limit is not None and p.used+p.held>=p.global_limit):raise ValidationError('Coupon is invalid, expired, exhausted or customer-ineligible.')
        indices=[i for i,u in enumerate(units) if not u['used'] and matches(p,u['product'])]
        subtotal=sum((units[i]['price'] for i in indices),Decimal(0))
        if not subtotal or subtotal<p.minimum:raise ValidationError('Coupon is not eligible for the undiscounted items.')
        amount=subtotal*p.value/100 if p.discount_type=='percent' else p.value
        amount=min(subtotal,amount,p.maximum if p.maximum is not None else subtotal)
        for i,share in zip(indices,allocate(amount,[units[i]['price'] for i in indices],exponent)):
            units[i]['discount']=share;units[i]['promotion']=p
    discounts=[sum((u['discount'] for u in units if u['line']==i),Decimal(0)) for i in range(len(lines))]
    ids=sorted({str(u['promotion'].id) for u in units if u['promotion'] is not None})
    if return_details:
        return discounts,ids,{'rule_version':2,'candidates':trace,'unit_net':[[str(u['price']-u['discount']) for u in units if u['line']==i] for i in range(len(lines))]}
    return discounts,ids

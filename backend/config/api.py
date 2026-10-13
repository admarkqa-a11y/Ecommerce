"""HTTP composition root. Business calculations live in domain services."""
import csv,io,json,uuid
import unicodedata
from datetime import timedelta
from decimal import Decimal
from django.db import transaction,models
from django.db.models import Q,Sum,Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers,viewsets
from rest_framework.decorators import api_view,permission_classes,action
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError,PermissionDenied,MethodNotAllowed
from apps.identity.permissions import StaffCapability
from apps.identity.models import Role
from apps.configuration.models import StoreSettings
from apps.catalog.models import Product,Variant,Category,Brand,Attribute,AttributeOption
from apps.catalog.services import public_product,publish,create_variant
from apps.inventory.models import Balance,Movement
from apps.inventory.services import adjust
from apps.delivery.models import Method,Area,Zone,Rule
from apps.promotions.models import Promotion
from apps.content.models import Page,Section
from apps.customers.models import Review,WishlistItem,Address
from apps.orders.models import Order,CartItem
from apps.orders import services as commerce
from apps.payments import services as payments
from apps.imports.models import ImportJob
from apps.imports import services as imports
from apps.operations.models import Audit
from apps.analytics.models import Event
from common.validation import whole_units

def serial(model,readonly=()):
    meta=type('Meta',(),{'model':model,'fields':'__all__','read_only_fields':['id','created_at','updated_at',*readonly]})
    return type(model.__name__+'Serializer',(serializers.ModelSerializer,),{'Meta':meta})

SettingsSerializer=serial(StoreSettings,['singleton','revision'])
PUBLIC_SETTINGS=['business_name','business_name_ar','tagline','tagline_ar','logo_url','favicon_url','primary_color','accent_color','phone','email','address','whatsapp','currency','currency_exponent','timezone','languages','social_links','cod_enabled','bank_enabled','bank_instructions','revision']

@api_view(['GET'])
@permission_classes([AllowAny])
def config(request):
    settings=StoreSettings.current()
    from apps.payments.adapters import card_enabled
    return Response({k:getattr(settings,k) for k in PUBLIC_SETTINGS}|{'tax_mode':'disabled','card_enabled':card_enabled()})

@api_view(['GET'])
@permission_classes([AllowAny])
def catalog(request,code=None):
    query=Product.objects.filter(status='active').exclude(publication={}).select_related('category','brand').order_by('name')
    if code:return Response(public_product(get_object_or_404(query,code=code)))
    def normalize(text):
        text=''.join(c for c in unicodedata.normalize('NFKD',str(text)) if not unicodedata.combining(c))
        return text.casefold().replace('ـ','')
    search=normalize(request.GET.get('q','').strip());category=request.GET.get('category');brand=request.GET.get('brand')
    try:
        page=whole_units(request.GET.get('page','1'),minimum=1,maximum=100000)
        limit=whole_units(request.GET.get('limit','30'),minimum=1,maximum=100)
        minimum=Decimal(request.GET['min_price']) if request.GET.get('min_price') else None
        maximum=Decimal(request.GET['max_price']) if request.GET.get('max_price') else None
        if any(v is not None and (not v.is_finite() or v<0) for v in [minimum,maximum]):raise ValueError()
    except (ValueError,ArithmeticError):raise ValidationError('Invalid price filter.')
    if minimum is not None and maximum is not None and minimum>maximum:raise ValidationError('Minimum price exceeds maximum.')
    tree={str(c.id):(c.code,str(c.parent_id) if c.parent_id else None) for c in Category.objects.all()}
    variant_filters={k[5:]:v for k,v in request.GET.items() if k.startswith('attr.')}
    if set(variant_filters)-set(Attribute.objects.filter(filterable=True).values_list('code',flat=True)):raise ValidationError('Unknown or nonfilterable attribute.')
    def matches(value,wanted):
        if isinstance(value,list):return any(matches(v,wanted) for v in value)
        if isinstance(value,bool):return str(value).lower()==wanted.lower()
        if isinstance(value,(int,float)):
            try:return Decimal(str(value))==Decimal(wanted)
            except ArithmeticError:return False
        return str(value)==wanted
    availability={str(b.variant_id):b.available for b in Balance.objects.filter(variant__product__in=query,variant__active=True)}
    values=[]
    for product in query:
        data=public_product(product,availability)
        descriptors={a['code']:a['value'] for a in data.get('attributes',[])}
        searchable=' '.join([data.get('name',''),data.get('name_ar',''),data.get('description',''),data.get('description_ar',''),json.dumps(descriptors,ensure_ascii=False),*[v['sku'] for v in data['variants']]])
        if search and search not in normalize(searchable):continue
        ancestors={data['category']['code']};node=data['category']['id'];seen=set()
        while node in tree and node not in seen:
            seen.add(node);label,node=tree[node];ancestors.add(label)
        if category and category not in ancestors:continue
        if brand and (not data['brand'] or data['brand']['id']!=brand):continue
        eligible=[]
        for v in data['variants']:
            if request.GET.get('in_stock')=='1' and v['available']<=0:continue
            if any(not matches(v['options'].get(k,{}).get('code',descriptors.get(k)),val) for k,val in variant_filters.items()):continue
            price=Decimal(v['sale_price'] if v['sale_price'] is not None else v['price'])
            try:
                if minimum is not None and price<minimum:continue
                if maximum is not None and price>maximum:continue
            except Exception:raise ValidationError('Invalid price filter.')
            eligible.append(v)
        if not eligible:continue
        data['matching_variant_ids']=[v['id'] for v in eligible]
        data['matched_price']=str(min(Decimal(v['sale_price'] if v['sale_price'] is not None else v['price']) for v in eligible))
        values.append(data)
    if request.GET.get('sort') in ['price_asc','price_desc']:
        values.sort(key=lambda p:(Decimal(p['matched_price']),p['code']),reverse=request.GET['sort']=='price_desc')
    else:values.sort(key=lambda p:(normalize(p.get('name','')),p['code']))
    start=(page-1)*limit
    return Response({'results':values[start:start+limit],'count':len(values),'limit':limit,'page':page,
        'next_page':page+1 if start+limit<len(values) else None})

@api_view(['GET'])
@permission_classes([AllowAny])
def public_lists(request,resource):
    registry={'categories':Category,'brands':Brand,'delivery-methods':Method,'delivery-areas':Area}
    if resource not in registry:raise ValidationError('Unknown resource.')
    model=registry[resource];qs=model.objects.all()
    if model==Method:qs=qs.filter(enabled=True)
    return Response(serial(model)(qs,many=True).data)

@api_view(['GET'])
@permission_classes([AllowAny])
def public_bundles(request):
    from apps.promotions.services import customer_eligible
    now=timezone.now();items=[]
    for p in Promotion.objects.filter(kind='bundle',enabled=True).filter(Q(starts_at__isnull=True)|Q(starts_at__lte=now)).filter(Q(ends_at__isnull=True)|Q(ends_at__gt=now)):
        if not customer_eligible(p,request.user if request.user.is_authenticated else None):continue
        if p.global_limit is not None and p.used+p.held>=p.global_limit:continue
        items.append({'id':str(p.id),'name':p.name,'components':p.rules.get('components',{}),'price':p.rules.get('price'),
            'currency':StoreSettings.current().currency})
    return Response(items)

@api_view(['POST'])
def promotion_preview(request):
    staff_check(request,'promotions.manage')
    from apps.promotions.services import calculate
    from apps.catalog.services import published_variant
    from apps.identity.models import User
    rows=request.data.get('lines',[])
    if not isinstance(rows,list) or not 1<=len(rows)<=50:raise ValidationError('Supply 1–50 preview lines.')
    lines=[]
    for row in rows:
        if not isinstance(row,dict):raise ValidationError('Each preview line must be an object.')
        variant=get_object_or_404(Variant,pk=row.get('variant_id'));pub=published_variant(variant)
        lines.append({'variant':variant,'quantity':whole_units(row.get('quantity',1),minimum=1,maximum=50),'price':pub['price'],'sale_price':pub['sale_price']})
    if sum(l['quantity'] for l in lines)>200:raise ValidationError('Preview limit is 200 units.')
    customer=get_object_or_404(User,pk=request.data['customer_id']) if request.data.get('customer_id') else None
    discounts,ids,detail=calculate(lines,request.data.get('coupon',''),StoreSettings.current().currency_exponent,customer=customer,return_details=True)
    return Response({'discounts':[str(d) for d in discounts],'promotion_ids':ids,**detail})

@api_view(['GET'])
@permission_classes([AllowAny])
def content(request,slug=None):
    if slug:
        page=get_object_or_404(Page,slug=slug,draft=False)
        return Response(page.publication)
    now=timezone.now();sections=Section.objects.filter(enabled=True).filter(Q(starts_at__isnull=True)|Q(starts_at__lte=now)).filter(Q(ends_at__isnull=True)|Q(ends_at__gt=now)).order_by('position')
    return Response({'sections':[s.publication for s in sections if s.publication],
        'pages':[p.publication for p in Page.objects.filter(draft=False)]})

@api_view(['GET','POST','PATCH','DELETE'])
@permission_classes([AllowAny])
def cart(request):
    if request.method!='GET':SessionAuthentication().enforce_csrf(request)
    c=commerce.get_cart(request)
    with transaction.atomic():
        c=type(c).objects.select_for_update().get(pk=c.pk)
        if request.method in ['POST','PATCH']:
            if 'coupon' in request.data:c.coupon=str(request.data['coupon'])[:50]
            else:
                variant=get_object_or_404(Variant,pk=request.data.get('variant_id'),active=True,product__status='active')
                qty=whole_units(request.data.get('quantity',1),minimum=1,maximum=50)
                item=c.items.filter(variant=variant).first()
                if request.method=='POST' and item:qty+=item.quantity
                if qty<1 or qty>50 or qty>variant.inventory.available:raise ValidationError('Quantity unavailable.')
                CartItem.objects.update_or_create(cart=c,variant=variant,defaults={'quantity':qty})
                if request.method=='POST':
                    from apps.analytics.services import track
                    track(request,'add_to_cart','add:'+str(uuid.uuid4()),{'variant_id':str(variant.id),'quantity':whole_units(request.data.get('quantity',1),minimum=1,maximum=50)})
            c.version+=1;c.save()
        if request.method=='DELETE':
            c.items.filter(id=request.data.get('item_id')).delete();c.version+=1;c.save()
    items=[]
    for item in c.items.select_related('variant__product'):
        p=item.variant.product.publication
        pub=next((v for v in p.get('variants',[]) if v['id']==str(item.variant_id)),{})
        items.append({'id':str(item.id),'variant_id':str(item.variant_id),'name':p.get('name',item.variant.product.name),'name_ar':p.get('name_ar',''),
            'sku':item.variant.sku,'price':pub.get('sale_price') or pub.get('price'),'quantity':item.quantity,'image_url':p.get('image_url','')})
    return Response({'id':str(c.id),'version':c.version,'coupon':c.coupon,'items':items,
        'bundles':[{'id':str(g.id),'promotion_id':str(g.promotion_id),'quantity':g.quantity} for g in c.bundles.all()]})

@api_view(['POST','DELETE'])
@permission_classes([AllowAny])
def cart_bundles(request):
    SessionAuthentication().enforce_csrf(request)
    from apps.orders.models import CartBundle
    c=commerce.get_cart(request)
    with transaction.atomic():
        c=type(c).objects.select_for_update().get(pk=c.pk)
        if request.method=='POST':
            promo=get_object_or_404(Promotion,pk=request.data.get('promotion_id'),enabled=True,kind='bundle')
            quantity=whole_units(request.data.get('quantity',1),minimum=1,maximum=10)
            promo.full_clean()
            CartBundle.objects.update_or_create(cart=c,promotion=promo,defaults={'quantity':quantity})
            from apps.analytics.services import track
            track(request,'add_to_cart','bundle:'+str(uuid.uuid4()),{'bundle_id':str(promo.id),'quantity':quantity})
        else:c.bundles.filter(pk=request.data.get('bundle_id')).delete()
        c.version+=1;c.save()
    return Response({'cart_id':str(c.id),'version':c.version})

@api_view(['POST'])
@permission_classes([AllowAny])
def quote(request):
    SessionAuthentication().enforce_csrf(request)
    q=commerce.make_quote(commerce.get_cart(request),request.data.get('method_id'),request.data.get('area_id'))
    return Response({'id':str(q.id),'expires_at':q.expires_at,**q.data})

def order_data(order):
    return {'id':str(order.id),'number':order.number,'state':order.state,'payment_state':order.payment_state,
        'payment_method':order.payment_method,'currency':order.currency,'total':str(order.total),'gross':str(order.gross),
        'discount':str(order.discount),'delivery_fee':str(order.delivery_fee),'tax':'0','contact':order.contact,
        'address':order.address,'created_at':order.created_at,
        'items':[dict(i.snapshot,id=str(i.id),restocked=i.restocked) for i in order.items.all()],
        'history':[{'action':h.action,'created_at':h.created_at} for h in order.history.order_by('created_at')],
        'refunds':serial(payments.Refund)(order.refunds.all(),many=True).data}

@api_view(['POST'])
@permission_classes([AllowAny])
def place(request):
    SessionAuthentication().enforce_csrf(request)
    order=commerce.place_order(request,request.data,request.headers.get('Idempotency-Key',''))
    result=order_data(order)
    if order.payment_method=='card' and order.total>0:
        from apps.payments.card import start
        attempt=start(order.id)
        order.refresh_from_db();result=order_data(order)
        result['payment']={'attempt_id':str(attempt.id),'state':attempt.state,'checkout_url':attempt.checkout_url or None}
    return Response(result,status=201)

@api_view(['POST'])
def reconcile_card(request,pk):
    staff_check(request,'payments.reconcile')
    from apps.payments.card import reconcile
    attempt=reconcile(pk,request.data.get('reference'))
    return Response({'id':str(attempt.id),'state':attempt.state,'issue':attempt.issue})

@api_view(['GET'])
def payment_attempts(request):
    staff_check(request,'payments.view')
    from apps.payments.models import PaymentAttempt
    return Response([{'id':str(a.id),'order_id':str(a.order_id),'provider':a.provider,'state':a.state,'reference':a.reference,'issue':a.issue} for a in PaymentAttempt.objects.order_by('-created_at')[:100]])

@api_view(['GET','POST'])
def notification_jobs(request,pk=None):
    staff_check(request,'operations.manage')
    if (pk and request.method!='POST') or (not pk and request.method!='GET'):raise MethodNotAllowed(request.method)
    from apps.operations.models import Outbox
    if request.method=='POST':
        with transaction.atomic():
            event=get_object_or_404(Outbox.objects.select_for_update(),pk=pk)
            if event.delivered_at:raise ValidationError('Already delivered notifications cannot be resent.')
            if event.claimed_at and event.claimed_at>timezone.now()-timedelta(minutes=10):raise ValidationError('Notification is currently claimed by a worker.')
            event.attempts=0;event.retry_at=None;event.claimed_at=None;event.save()
        return Response({'queued':True})
    return Response([{'id':str(e.id),'type':e.event_type,'attempts':e.attempts,'delivered_at':e.delivered_at,'retry_at':e.retry_at,'last_error':e.last_error}
        for e in Outbox.objects.order_by('-created_at')[:100]])

@api_view(['GET'])
@permission_classes([AllowAny])
def my_orders(request,order_id=None):
    qs=Order.objects.filter(owner=request.user) if request.user.is_authenticated else Order.objects.filter(owner__isnull=True,session_key=request.session.session_key or 'no-session')
    if order_id:return Response(order_data(get_object_or_404(qs,pk=order_id)))
    return Response([order_data(o) for o in qs.order_by('-created_at')[:100]])

@api_view(['GET'])
@permission_classes([AllowAny])
def invoice(request,order_id):
    qs=Order.objects.filter(owner=request.user) if request.user.is_authenticated else Order.objects.filter(owner__isnull=True,session_key=request.session.session_key or 'no-session')
    if request.user.is_authenticated and request.user.can('documents.view') and request.session.get('staff_mfa'):qs=Order.objects.all()
    o=get_object_or_404(qs,pk=order_id)
    from django.utils.html import escape
    rows=''.join(f'<tr><td>{escape(i.snapshot["name"])}</td><td>{i.quantity}</td><td>{i.net:.2f}</td></tr>' for i in o.items.all())
    html=f'''<!doctype html><html><head><meta charset="utf-8"><title>Invoice {escape(o.number)}</title><style>body{{font:16px Arial;max-width:800px;margin:60px auto;color:#172a26}}table{{width:100%;border-collapse:collapse}}td,th{{padding:16px;border-bottom:1px solid #ddd;text-align:start}}@media print{{button{{display:none}}}}</style></head><body><h1>{escape(o.business_snapshot.get('name',''))}</h1><p>{escape(o.business_snapshot.get('address',''))}</p><h2>Invoice / فاتورة · {escape(o.number)}</h2><p>{escape(o.contact.get('name',''))} · {escape(o.contact.get('email',''))}</p><p>Payment status / حالة الدفع: {escape(o.payment_state)}</p><table><thead><tr><th>Product / المنتج</th><th>Qty / العدد</th><th>Net / الصافي</th></tr></thead><tbody>{rows}</tbody></table><p>Delivery / التوصيل: {o.delivery_fee:.2f}</p><p>Tax / الضريبة: 0</p><h2>Total / الإجمالي: {o.total:.2f} {escape(o.currency)}</h2><button onclick="window.print()">Print / Save PDF</button></body></html>'''
    response=HttpResponse(html);response['Cache-Control']='private, no-store';return response

REGISTRY={
 'products':(Product,'catalog.view','catalog.manage',['publication','version','status']),
 'categories':(Category,'catalog.view','catalog.manage',[]),
 'brands':(Brand,'catalog.view','catalog.manage',[]),
 'attributes':(Attribute,'catalog.view','catalog.manage',[]),
 'attribute-options':(AttributeOption,'catalog.view','catalog.manage',[]),
 'variants':(Variant,'catalog.view','catalog.manage',['product','combination_key','sku']),
 'delivery-zones':(Zone,'delivery.view','delivery.manage',[]),
 'delivery-areas':(Area,'delivery.view','delivery.manage',[]),
 'delivery-methods':(Method,'delivery.view','delivery.manage',[]),
 'delivery-rules':(Rule,'delivery.view','delivery.manage',[]),
 'promotions':(Promotion,'promotions.view','promotions.manage',['used','held']),
 'pages':(Page,'content.view','content.manage',['publication','draft']),
 'homepage-sections':(Section,'content.view','content.manage',['publication']),
 'roles':(Role,'roles.manage','roles.manage',[]),
 'reviews':(Review,'reviews.moderate','reviews.moderate',['owner','product','rating','body']),
}

def create_viewset(model,read,write,readonly):
    base_serializer=serial(model,readonly)
    class ResourceSerializer(base_serializer):
        def get_fields(self):
            fields=super().get_fields()
            request=self.context.get('request')
            schema_view=getattr(self.context.get('view'),'swagger_fake_view',False)
            if model==Variant and not schema_view and (not request or not request.user.is_authenticated or not request.user.can('catalog.cost')):fields.pop('cost_price',None)
            return fields
        def validate(self,attrs):
            if model==Variant and 'cost_price' in self.initial_data and not self.context['request'].user.can('catalog.cost'):raise PermissionDenied('Cost permission required.')
            if model==Promotion:
                kind=attrs.get('kind',getattr(self.instance,'kind',None))
                if self.instance is None and 'priority' not in attrs:
                    from apps.promotions.models import PRIORITIES
                    attrs['priority']=PRIORITIES.get(kind,400)
                value=attrs.get('value',getattr(self.instance,'value',0));discount_type=attrs.get('discount_type',getattr(self.instance,'discount_type','percent'))
                if value<0 or (discount_type=='percent' and value>100):raise ValidationError('Invalid discount amount.')
            if model==Role:
                for cap in attrs.get('capabilities',[]):
                    if not self.context['request'].user.can(cap):raise PermissionDenied('Cannot grant a capability you do not possess.')
            if model==Rule:
                if attrs.get('fee',0)<0 or attrs.get('minimum',0)<0:raise ValidationError('Fees and minimums must be nonnegative.')
            return attrs
    class ResourceView(viewsets.ModelViewSet):
        serializer_class=ResourceSerializer
        permission_classes=[StaffCapability]
        capability={'GET':read,'POST':write,'PUT':write,'PATCH':write,'DELETE':write}
        queryset=model.objects.all().order_by('-created_at')
        @transaction.atomic
        def perform_create(self,serializer):
            if model==Variant:raise ValidationError('Create variants through the product variants action.')
            scalar={k:v for k,v in serializer.validated_data.items() if not model._meta.get_field(k).many_to_many}
            candidate=model(**scalar);candidate.full_clean()
            instance=serializer.save()
            Audit.objects.create(actor=self.request.user,action='create',resource=f'{model.__name__}:{instance.pk}')
        @transaction.atomic
        def perform_update(self,serializer):
            candidate=serializer.instance
            for k,v in serializer.validated_data.items():
                if not model._meta.get_field(k).many_to_many:setattr(candidate,k,v)
            candidate.full_clean()
            instance=serializer.save()
            Audit.objects.create(actor=self.request.user,action='update',resource=f'{model.__name__}:{instance.pk}')
        def perform_destroy(self,instance):
            if model==AttributeOption:
                from apps.catalog.models import ProductAttribute
                for value in ProductAttribute.objects.filter(attribute=instance.attribute).values_list('value',flat=True):
                    if value==instance.code or (isinstance(value,list) and instance.code in value):raise ValidationError('This option is used by a descriptive product attribute.')
            if model==Product:instance.status='archived';instance.save()
            elif model==Variant:instance.active=False;instance.save()
            else:instance.delete()
    ResourceSerializer.__name__=model.__name__+'ResourceSerializer'
    ResourceView.__name__=model.__name__+'ResourceViewSet'
    return ResourceView

class StaffView(viewsets.ViewSet):
    permission_classes=[StaffCapability]
    capability='settings.view'

def staff_check(request,capability):
    if not request.user.is_authenticated or not request.user.can(capability) or not request.session.get('staff_mfa'):raise PermissionDenied('Staff permission and MFA required.')

@api_view(['GET'])
def resources(request):
    if not request.user.is_staff or not request.session.get('staff_mfa'):raise PermissionDenied()
    result=[]
    for name,(model,read,write,readonly) in REGISTRY.items():
        if not request.user.can(read):continue
        fields=[]
        for f in model._meta.fields:
            if f.name in ['id','created_at','updated_at',*readonly]:continue
            if f.name=='cost_price' and not request.user.can('catalog.cost'):continue
            relation=next((n for n,(m,*_) in REGISTRY.items() if f.is_relation and m==f.related_model),None)
            fields.append({'name':f.name,'label':str(f.verbose_name),'type':f.get_internal_type(),
                'required':not f.blank and not f.null and not f.has_default(),'choices':list(f.choices or []),'relation':relation})
        result.append({'name':name,'fields':fields,'writable':request.user.can(write)})
    return Response(result)

@api_view(['GET','PATCH'])
def admin_settings(request):
    staff_check(request,'settings.manage' if request.method=='PATCH' else 'settings.view')
    cfg=StoreSettings.current()
    if request.method=='PATCH':
        ser=SettingsSerializer(cfg,data=request.data,partial=True);ser.is_valid(raise_exception=True)
        with transaction.atomic():
            cfg=StoreSettings.objects.select_for_update().get(pk=cfg.pk)
            for key,value in ser.validated_data.items():setattr(cfg,key,value)
            cfg.full_clean();cfg.revision+=1;cfg.save()
            Audit.objects.create(actor=request.user,action='settings.update',resource=str(cfg.id))
    return Response(SettingsSerializer(cfg).data)

@api_view(['POST'])
def publish_resource(request,resource,pk):
    if resource=='products':staff_check(request,'catalog.publish');obj=get_object_or_404(Product,pk=pk);publish(obj)
    elif resource=='pages':
        staff_check(request,'content.publish');obj=get_object_or_404(Page,pk=pk)
        if not obj.title_ar:raise ValidationError('Arabic title required.')
        obj.publication={k:getattr(obj,k) for k in ['slug','kind','title','title_ar','body','body_ar','seo_title','meta_description']};obj.draft=False;obj.save()
    elif resource=='homepage-sections':
        staff_check(request,'content.publish');obj=get_object_or_404(Section,pk=pk)
        obj.publication={k:getattr(obj,k) for k in ['kind','title','title_ar','body','body_ar','properties']};obj.save()
    else:raise ValidationError('Unknown publish resource.')
    return Response({'published':True})

@api_view(['POST'])
def add_variant(request,pk):
    staff_check(request,'catalog.manage');p=get_object_or_404(Product,pk=pk)
    if request.data.get('cost_price') is not None:staff_check(request,'catalog.cost')
    stock=whole_units(request.data.get('stock',0))
    if stock:staff_check(request,'inventory.adjust')
    v=create_variant(p,request.data.get('sku'),request.data.get('price'),request.data.get('options',{}),
        request.data.get('sale_price'),request.data.get('cost_price'),stock)
    return Response({'id':str(v.id),'sku':v.sku},status=201)

@api_view(['GET','PUT','PATCH'])
def product_attributes(request,pk):
    staff_check(request,'catalog.view' if request.method=='GET' else 'catalog.manage')
    product=get_object_or_404(Product,pk=pk)
    if request.method!='GET':
        from apps.catalog.services import set_attributes
        values=request.data.get('values')
        if not isinstance(values,dict):raise ValidationError('values must be an attribute-code object.')
        with transaction.atomic():
            product=Product.objects.select_for_update().get(pk=pk)
            set_attributes(product,values)
            if request.method=='PUT':product.attribute_values.exclude(attribute__code__in=values).delete()
            product.save()  # Changes the import dependency revision; publication is explicit.
            Audit.objects.create(actor=request.user,action='catalog.attributes',resource=str(product.id))
    return Response({'values':{value.attribute.code:value.value for value in product.attribute_values.select_related('attribute')}})

@api_view(['GET','POST','PATCH','DELETE'])
def addresses(request,pk=None):
    if request.method=='DELETE' and not pk:raise MethodNotAllowed(request.method)
    if request.method=='GET':
        if pk:return Response(serial(Address,['owner'])(get_object_or_404(Address,pk=pk,owner=request.user)).data)
        return Response(serial(Address,['owner'])(Address.objects.filter(owner=request.user).order_by('created_at'),many=True).data)
    if request.method=='DELETE':
        get_object_or_404(Address,pk=pk,owner=request.user).delete();return Response(status=204)
    if (request.method=='POST' and pk) or (request.method=='PATCH' and not pk):raise MethodNotAllowed(request.method)
    instance=get_object_or_404(Address,pk=pk,owner=request.user) if pk else None
    serializer=serial(Address,['owner'])(instance,data=request.data,partial=request.method=='PATCH')
    serializer.is_valid(raise_exception=True)
    data=serializer.validated_data.get('data',getattr(instance,'data',None))
    allowed={'name','phone','line1','line2','city','postal_code','area_id'}
    if not isinstance(data,dict) or set(data)-allowed or not isinstance(data.get('line1'),str) or not data['line1'].strip():raise ValidationError('Address needs line1 and only supported address fields.')
    if any(not isinstance(value,str) or len(value)>500 for value in data.values()):raise ValidationError('Address values must be text of at most 500 characters.')
    if data.get('area_id'):get_object_or_404(Area,pk=data['area_id'])
    saved=serializer.save(owner=request.user)
    return Response(serial(Address,['owner'])(saved).data,status=201 if request.method=='POST' else 200)

@api_view(['GET','POST'])
def inventory(request):
    staff_check(request,'inventory.adjust' if request.method=='POST' else 'inventory.view')
    if request.method=='POST':
        delta=request.data.get('delta')
        if not isinstance(delta,int) or isinstance(delta,bool):raise ValidationError('Delta must be an integer.')
        key=request.headers.get('Idempotency-Key','')
        if not key:raise ValidationError('Idempotency-Key required.')
        adjust(request.data.get('variant_id'),delta,request.data.get('reason',''),key,request.user)
    return Response([{'id':str(b.id),'variant_id':str(b.variant_id),'sku':b.variant.sku,'name':b.variant.product.name,'on_hand':b.on_hand,'reserved':b.reserved,'committed':b.committed,'available':b.available,'threshold':b.variant.product.threshold} for b in Balance.objects.select_related('variant__product').order_by('variant__sku')])

@api_view(['GET','POST'])
def admin_orders(request,pk=None,command=None):
    if request.method=='GET':
        if command:raise MethodNotAllowed('GET')
        staff_check(request,'orders.view')
        return Response(order_data(get_object_or_404(Order,pk=pk)) if pk else [order_data(o) for o in Order.objects.order_by('-created_at')[:100]])
    key=request.headers.get('Idempotency-Key','')
    if command=='transition':
        action=request.data.get('action');staff_check(request,'orders.cancel' if action=='cancel' else 'orders.transition')
        commerce.transition(pk,action,request.user,request.data.get('reason',''))
    elif command=='collect':
        order=get_object_or_404(Order,pk=pk);staff_check(request,'payments.verify_bank' if order.payment_method=='bank' else 'payments.collect')
        payments.record_capture(pk,request.data.get('reference',''),key,request.user)
    elif command=='refund':
        staff_check(request,'payments.refund')
        if 'items' in request.data:
            r=payments.request_item_refund(pk,request.data['items'],request.data.get('delivery_amount',0),request.data.get('reason',''),key,request.user)
        else:r=payments.request_refund(pk,request.data.get('amount'),request.data.get('reason',''),key,request.user)
        return Response(serial(payments.Refund)(r).data)
    elif command=='restock':
        staff_check(request,'inventory.adjust')
        if not key:raise ValidationError('Idempotency-Key required.')
        commerce.restock(pk,request.data.get('item_id'),whole_units(request.data.get('quantity',0),minimum=1),key,request.user)
    else:raise ValidationError('Unknown order command.')
    return Response(order_data(Order.objects.get(pk=pk)))

@api_view(['POST'])
def confirm_refund(request,pk):
    staff_check(request,'payments.refund')
    return Response(serial(payments.Refund)(payments.confirm_refund(pk,request.data.get('reference'),request.user)).data)

@api_view(['GET','POST'])
def import_jobs(request,pk=None,command=None):
    staff_check(request,'imports.manage')
    if pk:
        existing=get_object_or_404(ImportJob,pk=pk)
        imports.check_permissions(existing.rows,request.user,existing.stock_mode,write=False)
    if request.method=='POST':
        if pk and not command:raise MethodNotAllowed('POST')
        if command=='confirm':job=imports.confirm(pk,request.data.get('plan_hash'),request.user)
        elif command in ['validate','dry-run']:job=imports.validate(existing,request.user)
        elif command:raise ValidationError('Unknown import command.')
        else:
            if not request.FILES.get('file'):raise ValidationError('CSV file required.')
            job=imports.upload(request.user,request.FILES['file'],request.data.get('mode','create'),request.data.get('stock_mode','preserve_existing'))
        return Response(serial(ImportJob)(job).data)
    if command=='errors':
        stream=io.StringIO();writer=csv.writer(stream)
        writer.writerow(['row_number','error_code','message'])
        for error in existing.errors:
            # Spreadsheet formula characters must stay literal in report exports.
            def safe(value):
                value=str(value)
                return "'"+value if value.startswith(('=','+','-','@','\t','\r','\n')) else value
            writer.writerow([safe(error.get('row','')),safe(error.get('code','')),safe(error.get('message',''))])
        response=HttpResponse(stream.getvalue(),content_type='text/csv; charset=utf-8')
        response['Content-Disposition']='attachment; filename="import-errors.csv"'
        response['Cache-Control']='private, no-store'
        return response
    if command:raise ValidationError('Unknown import command.')
    if pk:return Response(serial(ImportJob)(existing).data)
    jobs=ImportJob.objects.order_by('-created_at')[:50]
    # List summaries never expose raw cost-bearing rows to another importer.
    return Response([{'id':str(job.id),'state':job.state,'mode':job.mode,'created_at':job.created_at,'row_count':len(job.rows),'error_count':len(job.errors),'result':job.result} for job in jobs])

@api_view(['GET'])
def dashboard(request):
    staff_check(request,'dashboard.view')
    from apps.analytics.services import dashboard as report
    return Response(report(request.query_params))

@api_view(['POST'])
@permission_classes([AllowAny])
def analytics_consent(request):
    SessionAuthentication().enforce_csrf(request)
    consent=request.data.get('consent')
    if not isinstance(consent,bool):raise ValidationError('consent must be true or false.')
    request.session['analytics_consent']=consent
    if not consent:request.session.pop('shopping_session_id',None)
    return Response({'consent':consent})

@api_view(['POST'])
@permission_classes([AllowAny])
def product_view(request):
    SessionAuthentication().enforce_csrf(request)
    from apps.analytics.services import track
    product=get_object_or_404(Product,pk=request.data.get('product_id'),status='active')
    try:page_id=str(uuid.UUID(str(request.data.get('page_view_id'))))
    except (ValueError,TypeError):raise ValidationError('page_view_id must be a UUID.')
    event=track(request,'product_view',f'view:{product.id}:{page_id}',{'product_id':str(product.id),'page_view_id':page_id})
    return Response({'recorded':event is not None})

@api_view(['GET','POST','DELETE'])
def wishlist(request):
    if request.method=='POST':WishlistItem.objects.get_or_create(owner=request.user,product=get_object_or_404(Product,pk=request.data.get('product_id'),status='active'))
    if request.method=='DELETE':WishlistItem.objects.filter(owner=request.user,product_id=request.data.get('product_id')).delete()
    return Response([public_product(w.product) for w in WishlistItem.objects.filter(owner=request.user,product__status='active').select_related('product')])

@api_view(['GET','POST'])
@permission_classes([AllowAny])
def reviews(request,product_id):
    p=get_object_or_404(Product,pk=product_id,status='active')
    if request.method=='POST':
        if not request.user.is_authenticated:raise PermissionDenied()
        SessionAuthentication().enforce_csrf(request)
        if not Order.objects.filter(owner=request.user,state__in=['delivered','collected'],items__variant__product=p).exists():raise PermissionDenied('A completed purchase is required.')
        review,_=Review.objects.update_or_create(owner=request.user,product=p,defaults={'rating':request.data.get('rating'),'body':str(request.data.get('body',''))[:5000],'status':'pending'})
        return Response({'status':review.status})
    return Response([{'rating':r.rating,'body':r.body,'name':r.owner.first_name,'created_at':r.created_at} for r in Review.objects.filter(product=p,status='approved').select_related('owner')])

import json
import math
from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Product, Attribute, AttributeOption, ProductAttribute, ProductAxis, Variant, VariantOption
from apps.inventory.models import Balance
from common.validation import whole_units

def validate_attribute(attribute, value):
    kind = attribute.data_type
    valid = True
    if kind == 'text': valid = isinstance(value,str)
    elif kind == 'number': valid = isinstance(value,(int,float)) and not isinstance(value,bool) and (not isinstance(value,float) or math.isfinite(value))
    elif kind == 'boolean': valid = isinstance(value,bool)
    elif kind == 'date':
        try: date.fromisoformat(value)
        except (ValueError,TypeError): valid = False
    elif kind in ['single_select','multi_select']:
        options = set(attribute.options.values_list('code',flat=True))
        valid = (isinstance(value,str) and value in options) if kind == 'single_select' else (
            isinstance(value,list) and all(isinstance(x,str) and x in options for x in value) and len(value)==len(set(value)))
    if not valid: raise ValidationError({attribute.code:'Value does not match the attribute type/options.'})

@transaction.atomic
def set_attributes(product, values):
    product=Product.objects.select_for_update().get(pk=product.pk)
    for code,value in values.items():
        try: attr = Attribute.objects.get(code=code)
        except Attribute.DoesNotExist: raise ValidationError(f'Unknown attribute: {code}')
        validate_attribute(attr,value)
        if product.axes.filter(attribute=attr).exists() and VariantOption.objects.filter(variant__product=product,attribute=attr).exclude(option__code=value).exists():
            raise ValidationError('A product-wide attribute cannot contradict its variant selections.')
        ProductAttribute.objects.update_or_create(product=product,attribute=attr,defaults={'value':value})

@transaction.atomic
def create_variant(product, sku, price, options=None, sale_price=None, cost_price=None, stock=0, barcode=''):
    product=Product.objects.select_for_update().get(pk=product.pk)
    stock = whole_units(stock)
    options = options or {}
    if not isinstance(options,dict):raise ValidationError('Variant options must be an object.')
    if product.variants.exists() and set(product.axes.values_list('attribute__code',flat=True))!=set(options):
        raise ValidationError('Existing variant axes cannot be changed when adding a variant.')
    axes = {}
    for code,option_code in sorted(options.items()):
        try:
            attr=Attribute.objects.get(code=code,variant_eligible=True,data_type='single_select')
            opt=AttributeOption.objects.get(attribute=attr,code=option_code)
        except (Attribute.DoesNotExist,AttributeOption.DoesNotExist): raise ValidationError('Invalid variant axis or option.')
        descriptive=ProductAttribute.objects.filter(product=product,attribute=attr).first()
        if descriptive and descriptive.value!=option_code:raise ValidationError('Variant selection contradicts the product-wide attribute.')
        axis,_=ProductAxis.objects.get_or_create(product=product,attribute=attr)
        axis.options.add(opt)
        axes[code]=(attr,opt)
    existing=set(product.axes.values_list('attribute__code',flat=True))
    if existing != set(options): raise ValidationError('Every variant must select exactly the configured axes.')
    if (product.kind=='simple') != (not options): raise ValidationError('Simple items have no axes; variable items require axes.')
    if product.variants.count()>=250: raise ValidationError('Maximum 250 variants per product.')
    key=json.dumps(options,sort_keys=True,separators=(',',':'))
    variant=Variant(product=product,sku=sku,price=price,sale_price=sale_price,cost_price=cost_price,barcode=barcode,combination_key=key)
    variant.full_clean();variant.save()
    for attr,opt in axes.values(): VariantOption.objects.create(variant=variant,attribute=attr,option=opt)
    Balance.objects.create(variant=variant,on_hand=0)
    if stock:
        from apps.inventory.services import adjust
        adjust(variant.id,stock,'Opening stock','opening:'+str(variant.id))
    return variant

def product_snapshot(product):
    return {
        'id':str(product.id),'code':product.code,'name':product.name,'name_ar':product.name_ar,
        'description':product.description,'description_ar':product.description_ar,'image_url':product.image_url,
        'kind':product.kind,'featured':product.featured,
        'category':{'id':str(product.category_id),'code':product.category.code,'name':product.category.name,'name_ar':product.category.name_ar},
        'brand':{'id':str(product.brand_id),'name':product.brand.name,'name_ar':product.brand.name_ar} if product.brand_id else None,
        'attributes':[{'code':v.attribute.code,'name':v.attribute.name,'name_ar':v.attribute.name_ar,'value':v.value,'unit':v.attribute.unit} for v in product.attribute_values.select_related('attribute')],
        'variants':[{'id':str(v.id),'sku':v.sku,'price':str(v.price),'sale_price':str(v.sale_price) if v.sale_price is not None else None,
            'image_url':v.image_url,'options':{o.attribute.code:{'code':o.option.code,'label':o.option.label,'label_ar':o.option.label_ar} for o in v.selected_options.select_related('attribute','option')}} for v in product.variants.filter(active=True)]}

@transaction.atomic
def publish(product):
    if not product.name_ar: raise ValidationError('Arabic name is required before publication.')
    if not product.variants.filter(active=True).exists(): raise ValidationError('Add a sellable variant before publishing.')
    product.publication=product_snapshot(product)
    product.status='active';product.version+=1;product.save()
    return product

def public_product(product,available=None):
    data=dict(product.publication)
    balances=available if available is not None else {str(b.variant_id):b.available for b in Balance.objects.filter(variant__product=product,variant__active=True)}
    data['variants']=[dict(v,available=balances.get(v['id'],0)) for v in data.get('variants',[]) if v['id'] in balances]
    return data

def published_variant(variant):
    if not variant.active or variant.product.status!='active': raise ValidationError('Product is unavailable.')
    match=next((v for v in variant.product.publication.get('variants',[]) if v['id']==str(variant.id)),None)
    if not match: raise ValidationError('Variant is not published.')
    return match

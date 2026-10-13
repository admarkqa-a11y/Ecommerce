import csv,io,json,hashlib,re
from decimal import Decimal,InvalidOperation
from django.db import transaction
from django.core.exceptions import ValidationError as ModelError
from rest_framework.exceptions import ValidationError,PermissionDenied
from common.api import Conflict
from apps.catalog.models import Product,Category,Brand,Attribute,Variant,ProductAxis
from apps.catalog.services import create_variant,set_attributes,validate_attribute,publish
from apps.inventory.models import Balance
from apps.inventory.services import adjust
from .models import ImportJob

HEADERS = set('product_code product_type name_en name_ar sku brand_code category_code subcategory_code price sale_price cost_price stock description_en description_ar attributes_json variant_attributes_json variant_sku variant_price variant_sale_price variant_stock barcode low_stock_threshold image_urls_json variant_image_url status'.split())

def check_permissions(rows, actor, stock_mode, *, write=True):
    if not actor.can('imports.manage'):raise PermissionDenied('Import permission required.')
    if any('cost_price' in row for row in rows) and not actor.can('catalog.cost'):
        raise PermissionDenied('Cost-price import permission required.')
    if not write:return
    if any(row.get('status')=='active' for row in rows) and not actor.can('catalog.publish'):
        raise PermissionDenied('Publication permission required.')
    if stock_mode=='replace_on_hand' and not actor.can('inventory.adjust'):
        raise PermissionDenied('Inventory adjustment permission required.')

def hash_data(data):return hashlib.sha256(json.dumps(data,sort_keys=True,default=str).encode()).hexdigest()

def dependency_hash():
    return hash_data({
        'products':list(Product.objects.order_by('id').values('id','updated_at')),
        'variants':list(Variant.objects.order_by('id').values('id','updated_at')),
        'inventory':list(Balance.objects.order_by('id').values('id','version')),
        'attributes':list(Attribute.objects.order_by('id').values('id','updated_at')),
        'options':list(Attribute.objects.order_by('id').values('id','options__id','options__updated_at')),
        'categories':list(Category.objects.order_by('id').values('id','updated_at')),
        'brands':list(Brand.objects.order_by('id').values('id','updated_at'))})

def upload(actor,uploaded,mode='create',stock_mode='preserve_existing'):
    if uploaded.size>10*1024*1024:raise ValidationError('CSV limit is 10 MiB.')
    if mode not in ['create','update','upsert'] or stock_mode not in ['preserve_existing','replace_on_hand']:raise ValidationError('Invalid import mode.')
    try:
        reader=csv.DictReader(io.StringIO(uploaded.read().decode('utf-8-sig')),strict=True)
        headers=reader.fieldnames or []
        if len(headers)!=len(set(headers)):raise ValidationError('Duplicate CSV headers are not allowed.')
        if set(headers)-HEADERS:raise ValidationError('Unknown CSV headers: '+', '.join(sorted(set(headers)-HEADERS)))
        if not {'product_code','product_type','name_en','category_code'}<=set(headers):
            raise ValidationError('Missing required CSV headers.')
        rows=list(reader)
    except (UnicodeDecodeError,csv.Error):raise ValidationError('Invalid UTF-8 CSV.')
    if not rows or len(rows)>5000:raise ValidationError('CSV requires 1–5000 rows.')
    if any(None in r or any(v is None for v in r.values()) for r in rows):raise ValidationError('CSV column counts do not match the header.')
    rows=[{k:v.strip() for k,v in row.items()} for row in rows]
    check_permissions(rows,actor,stock_mode)
    job=ImportJob.objects.create(actor=actor,rows=rows,mode=mode,stock_mode=stock_mode)
    return validate(job)

@transaction.atomic
def validate(job, actor=None):
    job=ImportJob.objects.select_for_update().get(pk=job.pk)
    actor=actor or job.actor
    check_permissions(job.rows,actor,job.stock_mode)
    if job.state=='committed':raise Conflict('A committed import cannot be revalidated.')
    errors=[];skus=set();combos=set();products={}
    for index,row in enumerate(job.rows,2):
        try:
            code=row.get('product_code','').strip();kind=row.get('product_type','')
            if not code or kind not in ['simple','variable'] or not row.get('name_en'):raise ValueError('Missing product code, type or English name.')
            if not re.fullmatch(r'[a-z0-9_-]+',code):raise ValueError('Product codes must use lowercase ASCII letters, digits, hyphens or underscores.')
            if row.get('image_urls_json','[]') not in ['','[]'] or row.get('variant_image_url'):
                raise ValueError('Remote image ingestion is not enabled in this release. Remove image URLs and upload assets separately.')
            category=Category.objects.get(code=row.get('subcategory_code') or row['category_code'])
            if row.get('subcategory_code') and (not category.parent_id or category.parent.code!=row['category_code']):raise ValueError('Subcategory parent mismatch.')
            if row.get('brand_code'):Brand.objects.get(code=row['brand_code'])
            existing=Product.objects.filter(code=code).first()
            if job.mode=='create' and existing:raise ValueError('Product already exists; use update or upsert.')
            if job.mode=='update' and not existing:raise ValueError('Product not found for update.')
            if existing and existing.kind!=kind:raise ValueError('Cannot change product type in import.')
            common={k:row.get(k,'') for k in ['name_en','name_ar','product_type','brand_code','category_code','subcategory_code','description_en','description_ar','attributes_json','low_stock_threshold','status','image_urls_json']}
            if code in products and products[code]!=common:raise ValueError('Conflicting product-level fields.')
            products[code]=common
            opts=json.loads(row.get('variant_attributes_json') or '{}')
            attrs=json.loads(row.get('attributes_json') or '{}')
            if not isinstance(opts,dict) or not isinstance(attrs,dict):raise ValueError('Attribute values must be JSON objects.')
            if (kind=='simple')!= (not opts):raise ValueError('Variant axis/type mismatch.')
            for attr_code,val in {**attrs,**opts}.items():
                attr=Attribute.objects.get(code=attr_code);validate_attribute(attr,val)
                if attr_code in opts and not attr.variant_eligible:raise ValueError('Attribute cannot define variants.')
            if existing and existing.axes.exists() and set(opts)!=set(existing.axes.values_list('attribute__code',flat=True)):raise ValueError('Existing variant axes cannot be changed by import.')
            sku=(row.get('variant_sku') if kind=='variable' else row.get('sku')) or ''
            if not sku or sku in skus:raise ValueError('Missing or duplicate SKU.')
            if not re.fullmatch(r'[A-Za-z0-9_-]+',sku):raise ValueError('SKUs must use ASCII letters, digits, hyphens or underscores.')
            skus.add(sku);combo=(code,json.dumps(opts,sort_keys=True))
            if combo in combos:raise ValueError('Duplicate variant combination.')
            combos.add(combo)
            current=Variant.objects.filter(sku=sku).first()
            if current and (not existing or current.product_id!=existing.id):raise ValueError('SKU belongs to a different product.')
            if current and json.loads(current.combination_key)!=opts:raise ValueError('SKU combination mismatch.')
            price=Decimal(row.get('variant_price') or row.get('price') or (str(current.price) if current else ''))
            sale_raw=row.get('variant_sale_price') or row.get('sale_price')
            sale=Decimal(sale_raw) if sale_raw and sale_raw!='__NULL__' else None
            if not price.is_finite() or price<0 or (sale is not None and (not sale.is_finite() or sale<0 or sale>=price)):raise ValueError('Invalid price/sale price.')
            cost_raw=row.get('cost_price')
            if cost_raw and cost_raw!='__NULL__' and (not Decimal(cost_raw).is_finite() or Decimal(cost_raw)<0):raise ValueError('Invalid cost.')
            stock_raw=row.get('variant_stock') if kind=='variable' else row.get('stock')
            if not current and not stock_raw:raise ValueError('Opening stock is required for a new variant, including zero.')
            stock=int(stock_raw) if stock_raw else (current.inventory.on_hand if current else 0)
            if stock<0:raise ValueError('Stock cannot be negative.')
            if current and job.stock_mode=='replace_on_hand' and stock<current.inventory.reserved+current.inventory.committed:raise ValueError('Stock is below allocated quantity.')
            if row.get('status','') not in ['','draft','active']:raise ValueError('Import status must be draft or active.')
            if row.get('status')=='active' and not actor.can('catalog.publish'):raise PermissionDenied('Publication permission required.')
        except Exception as exc:
            errors.append({'row':index,'code':'INVALID_ROW','message':str(exc)[:500]})
    if not errors:
        # Use the exact commit path in a savepoint, then roll it back. This catches
        # relational/model constraints, publication failures and cross-row conflicts.
        try:
            with transaction.atomic():
                apply_rows(job,actor)
                transaction.set_rollback(True)
        except RowError as exc:
            errors.append({'row':exc.row,'code':'INVALID_ROW','message':str(exc)[:500]})
    job.errors=errors;job.dependency_hash=dependency_hash()
    job.plan_hash=hash_data({'rows':job.rows,'dependencies':job.dependency_hash,'mode':job.mode,'stock_mode':job.stock_mode})
    job.state='invalid' if errors else 'previewed';job.save()
    return job

@transaction.atomic
def confirm(job_id,plan_hash,actor):
    job=ImportJob.objects.select_for_update().get(pk=job_id)
    check_permissions(job.rows,actor,job.stock_mode)
    if job.plan_hash!=plan_hash:raise Conflict('Import plan hash does not match.')
    if job.state=='committed':return job
    if job.state!='previewed' or job.plan_hash!=plan_hash:raise Conflict('Import has no valid confirmed preview.')
    list(Balance.objects.select_for_update().order_by('variant_id'))
    if dependency_hash()!=job.dependency_hash:raise Conflict('Catalog or stock changed. Validate again before confirming.')
    try:job.result=apply_rows(job,actor)
    except RowError as exc:raise Conflict(f'Import rejected at row {exc.row}; no records imported: {exc}')
    job.state='committed';job.save()
    return job

class RowError(Exception):
    def __init__(self,row,error):
        self.row=row
        super().__init__(str(error))

def apply_rows(job,actor):
    products={};variant_count=0
    for row_number,row in enumerate(job.rows,2):
      try:
        code=row['product_code'];kind=row['product_type']
        if code not in products:
            defaults={'name':row['name_en'],'name_ar':row.get('name_ar',''),'kind':kind,
                'category':Category.objects.get(code=row.get('subcategory_code') or row['category_code']),
                'brand':Brand.objects.get(code=row['brand_code']) if row.get('brand_code') else None,
                'description':row.get('description_en',''),'description_ar':row.get('description_ar',''),
                'threshold':int(row.get('low_stock_threshold') or 5)}
            product=Product.objects.filter(code=code).first()
            if product:
                # Blank optional product fields preserve existing values on update.
                for field,column in [('name_ar','name_ar'),('description','description_en'),('description_ar','description_ar'),('threshold','low_stock_threshold')]:
                    if not row.get(column):defaults.pop(field,None)
                if not row.get('brand_code'):defaults.pop('brand',None)
                for field,value in defaults.items():setattr(product,field,value)
            else:product=Product(code=code,**defaults)
            product.full_clean();product.save()
            set_attributes(product,json.loads(row.get('attributes_json') or '{}'));products[code]=product
        product=products[code];sku=row['variant_sku'] if kind=='variable' else row['sku']
        current=Variant.objects.filter(sku=sku).first()
        price=Decimal(row.get('variant_price') or row.get('price') or str(current.price))
        sale_raw=row.get('variant_sale_price') or row.get('sale_price')
        sale=Decimal(sale_raw) if sale_raw and sale_raw!='__NULL__' else (current.sale_price if current and sale_raw!='__NULL__' else None)
        cost_raw=row.get('cost_price');cost=Decimal(cost_raw) if cost_raw and cost_raw!='__NULL__' else (current.cost_price if current and cost_raw!='__NULL__' else None)
        stock_raw=row.get('variant_stock') if kind=='variable' else row.get('stock');stock=int(stock_raw) if stock_raw else (current.inventory.on_hand if current else 0)
        if not current:
            create_variant(product,sku,price,json.loads(row.get('variant_attributes_json') or '{}'),sale,cost,stock,row.get('barcode',''))
        else:
            current.price=price;current.sale_price=sale;current.cost_price=cost;current.full_clean();current.save()
            if job.stock_mode=='replace_on_hand':
                if not actor.can('inventory.adjust'):raise PermissionDenied()
                adjust(current.id,stock-current.inventory.on_hand,'Confirmed CSV stock replacement',f'import:{job.id}:{current.id}',actor)
        variant_count+=1
      except Exception as exc:raise RowError(row_number,exc) from exc
    for row_number,row in enumerate(job.rows,2):
      try:
        if row.get('status')=='active':publish(products[row['product_code']])
      except Exception as exc:raise RowError(row_number,exc) from exc
    return {'products':len(products),'variants':variant_count}

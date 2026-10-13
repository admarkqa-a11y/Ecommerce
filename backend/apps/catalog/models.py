import json
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from common.models import Entity

class Named(Entity):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    name_ar = models.CharField(max_length=200, blank=True)
    class Meta:
        abstract = True

class Category(Named):
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT)
    def clean(self):
        seen = {self.pk}
        node = self.parent
        while node:
            if node.pk in seen: raise ValidationError('Category hierarchy cannot contain a cycle.')
            seen.add(node.pk)
            node = node.parent

class Brand(Named):
    pass

class Attribute(Named):
    data_type = models.CharField(max_length=20, choices=[(v,v) for v in ['text','number','boolean','date','single_select','multi_select']])
    unit = models.CharField(max_length=30, blank=True)
    filterable = models.BooleanField(default=True)
    comparable = models.BooleanField(default=True)
    variant_eligible = models.BooleanField(default=False)
    def clean(self):
        if self.variant_eligible and self.data_type != 'single_select':
            raise ValidationError('Variant axes must be single-select attributes.')
        old=Attribute.objects.filter(pk=self.pk).first()
        if old and (old.code!=self.code or old.data_type!=self.data_type) and (
            ProductAttribute.objects.filter(attribute=self).exists() or ProductAxis.objects.filter(attribute=self).exists()):
            raise ValidationError('An in-use attribute code/type requires an explicit data migration.')
        if old and not self.variant_eligible and ProductAxis.objects.filter(attribute=self).exists():
            raise ValidationError('An existing variant axis cannot be made ineligible.')

class AttributeOption(Entity):
    attribute = models.ForeignKey(Attribute, on_delete=models.PROTECT, related_name='options')
    code = models.SlugField()
    label = models.CharField(max_length=150)
    label_ar = models.CharField(max_length=150, blank=True)
    def clean(self):
        old=AttributeOption.objects.filter(pk=self.pk).first()
        if old and (old.code!=self.code or old.attribute_id!=self.attribute_id) and (
            VariantOption.objects.filter(option=self).exists() or ProductAttribute.objects.filter(attribute_id=old.attribute_id).exists()):
            raise ValidationError('An in-use option code/attribute cannot be changed.')
    class Meta:
        constraints = [models.UniqueConstraint(fields=['attribute','code'],name='option_code_unique')]

class Product(Named):
    kind = models.CharField(max_length=12, choices=[('simple','Simple'),('variable','Variable')], default='simple')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    description = models.TextField(blank=True)
    description_ar = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    status = models.CharField(max_length=12, choices=[('draft','Draft'),('active','Active'),('archived','Archived')],default='draft')
    featured = models.BooleanField(default=False)
    threshold = models.PositiveIntegerField(default=5)
    version = models.PositiveIntegerField(default=1)
    publication = models.JSONField(default=dict, blank=True)

    def clean(self):
        old=Product.objects.filter(pk=self.pk).first()
        if old and old.kind!=self.kind and old.variants.exists():
            raise ValidationError('Archive/rebuild variants explicitly before changing the product type.')

class ProductAttribute(Entity):
    product = models.ForeignKey(Product, related_name='attribute_values', on_delete=models.CASCADE)
    attribute = models.ForeignKey(Attribute,on_delete=models.PROTECT)
    value = models.JSONField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['product','attribute'],name='product_attribute_unique')]
    def clean(self):
        from .services import validate_attribute
        validate_attribute(self.attribute, self.value)

class ProductAxis(Entity):
    product = models.ForeignKey(Product,related_name='axes',on_delete=models.CASCADE)
    attribute = models.ForeignKey(Attribute,on_delete=models.PROTECT)
    options = models.ManyToManyField(AttributeOption)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['product','attribute'],name='product_axis_unique')]

class Variant(Entity):
    product = models.ForeignKey(Product,related_name='variants',on_delete=models.PROTECT)
    sku = models.CharField(max_length=100,unique=True)
    barcode = models.CharField(max_length=100,blank=True)
    combination_key = models.CharField(max_length=2000,blank=True)
    price = models.DecimalField(max_digits=20,decimal_places=6)
    sale_price = models.DecimalField(max_digits=20,decimal_places=6,null=True,blank=True)
    cost_price = models.DecimalField(max_digits=20,decimal_places=6,null=True,blank=True)
    image_url = models.URLField(blank=True)
    active = models.BooleanField(default=True)
    def clean(self):
        if self.cost_price is not None and self.cost_price<0:raise ValidationError('Cost price must be nonnegative.')
    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['product','combination_key'],name='variant_combination_unique'),
            models.UniqueConstraint(fields=['barcode'],condition=~Q(barcode=''),name='variant_nonempty_barcode_unique'),
            models.CheckConstraint(condition=Q(price__gte=0),name='variant_price_nonnegative'),
            models.CheckConstraint(condition=Q(sale_price__isnull=True)|(Q(sale_price__gte=0)&Q(sale_price__lt=models.F('price'))),name='valid_sale_price'),
        ]

class VariantOption(Entity):
    variant = models.ForeignKey(Variant,related_name='selected_options',on_delete=models.CASCADE)
    attribute = models.ForeignKey(Attribute,on_delete=models.PROTECT)
    option = models.ForeignKey(AttributeOption,on_delete=models.PROTECT)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['variant','attribute'],name='variant_axis_once')]

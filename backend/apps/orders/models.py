import secrets
from django.db import models
from common.models import Entity

def order_number(): return 'ORD-'+secrets.token_hex(5).upper()

class Cart(Entity):
    owner = models.ForeignKey('identity.User',null=True,blank=True,on_delete=models.PROTECT)
    session_key = models.CharField(max_length=64)
    coupon = models.CharField(max_length=50,blank=True)
    version = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    shopping_session = models.ForeignKey('analytics.ShoppingSession',null=True,on_delete=models.SET_NULL)

class CartItem(Entity):
    cart = models.ForeignKey(Cart,related_name='items',on_delete=models.CASCADE)
    variant = models.ForeignKey('catalog.Variant',on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['cart','variant'],name='cart_variant_unique'),models.CheckConstraint(condition=models.Q(quantity__gt=0),name='cart_quantity_positive')]

class CartBundle(Entity):
    cart = models.ForeignKey(Cart,related_name='bundles',on_delete=models.CASCADE)
    promotion = models.ForeignKey('promotions.Promotion',on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['cart','promotion'],name='cart_bundle_once')]

class Quote(Entity):
    cart = models.ForeignKey(Cart,on_delete=models.PROTECT)
    cart_version = models.PositiveIntegerField()
    data = models.JSONField()
    digest = models.CharField(max_length=64)
    expires_at = models.DateTimeField()

class Order(Entity):
    number = models.CharField(max_length=30,default=order_number,unique=True)
    owner = models.ForeignKey('identity.User',null=True,blank=True,on_delete=models.PROTECT)
    session_key = models.CharField(max_length=64)
    cart = models.OneToOneField(Cart,on_delete=models.PROTECT)
    contact = models.JSONField()
    address = models.JSONField(default=dict, blank=True)
    business_snapshot = models.JSONField(default=dict, blank=True)
    currency = models.CharField(max_length=3)
    exponent = models.PositiveSmallIntegerField(default=2)
    method = models.ForeignKey('delivery.Method',on_delete=models.PROTECT)
    payment_method = models.CharField(max_length=20)
    state = models.CharField(max_length=30,default='pending')
    payment_state = models.CharField(max_length=30,default='pending')
    gross = models.DecimalField(max_digits=20,decimal_places=6)
    discount = models.DecimalField(max_digits=20,decimal_places=6,default=0)
    delivery_fee = models.DecimalField(max_digits=20,decimal_places=6,default=0)
    tax = models.DecimalField(max_digits=20,decimal_places=6,default=0)
    total = models.DecimalField(max_digits=20,decimal_places=6)
    accepted_at = models.DateTimeField(null=True)
    expires_at = models.DateTimeField(null=True)
    departed_at = models.DateTimeField(null=True)
    cancelled_at = models.DateTimeField(null=True)
    idempotency_key = models.CharField(max_length=200,unique=True)
    request_hash = models.CharField(max_length=64)
    promotions = models.ManyToManyField('promotions.Promotion',blank=True)
    shopping_session = models.ForeignKey('analytics.ShoppingSession',null=True,on_delete=models.SET_NULL)

class OrderItem(Entity):
    order = models.ForeignKey(Order,related_name='items',on_delete=models.PROTECT)
    variant = models.ForeignKey('catalog.Variant',on_delete=models.PROTECT)
    snapshot = models.JSONField()
    quantity = models.PositiveIntegerField()
    gross = models.DecimalField(max_digits=20,decimal_places=6)
    discount = models.DecimalField(max_digits=20,decimal_places=6)
    net = models.DecimalField(max_digits=20,decimal_places=6)
    restocked = models.PositiveIntegerField(default=0)

class History(Entity):
    order = models.ForeignKey(Order,related_name='history',on_delete=models.PROTECT)
    action = models.CharField(max_length=40)
    actor = models.ForeignKey('identity.User',on_delete=models.PROTECT,null=True)
    reason = models.TextField(blank=True)

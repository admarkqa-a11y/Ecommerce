from django.db import models
from common.models import Entity

class Address(Entity):
    owner = models.ForeignKey('identity.User',on_delete=models.CASCADE)
    label = models.CharField(max_length=60)
    data = models.JSONField()

class WishlistItem(Entity):
    owner = models.ForeignKey('identity.User',on_delete=models.CASCADE)
    product = models.ForeignKey('catalog.Product',on_delete=models.PROTECT)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['owner','product'],name='wishlist_unique')]

class Review(Entity):
    owner = models.ForeignKey('identity.User',on_delete=models.PROTECT)
    product = models.ForeignKey('catalog.Product',on_delete=models.PROTECT)
    rating = models.PositiveSmallIntegerField()
    body = models.TextField()
    status = models.CharField(max_length=15,default='pending')
    class Meta:
        constraints=[models.UniqueConstraint(fields=['owner','product'],name='review_unique'),models.CheckConstraint(condition=models.Q(rating__gte=1,rating__lte=5),name='review_rating_range')]


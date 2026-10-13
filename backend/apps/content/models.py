from django.db import models
from common.models import Entity

class Page(Entity):
    slug = models.SlugField(unique=True)
    kind = models.CharField(max_length=20,choices=[('page','Page'),('blog','Blog')],default='page')
    title = models.CharField(max_length=200)
    title_ar = models.CharField(max_length=200,blank=True)
    body = models.TextField(blank=True)
    body_ar = models.TextField(blank=True)
    seo_title = models.CharField(max_length=200,blank=True)
    meta_description = models.CharField(max_length=300,blank=True)
    draft = models.BooleanField(default=True)
    publication = models.JSONField(default=dict,blank=True)

class Section(Entity):
    kind = models.CharField(max_length=30,choices=[(x,x) for x in ['hero','featured_products','categories','brands','text','promotion']])
    title = models.CharField(max_length=200)
    title_ar = models.CharField(max_length=200,blank=True)
    body = models.TextField(blank=True)
    body_ar = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True,blank=True)
    ends_at = models.DateTimeField(null=True,blank=True)
    properties = models.JSONField(default=dict,blank=True)
    publication = models.JSONField(default=dict,blank=True)


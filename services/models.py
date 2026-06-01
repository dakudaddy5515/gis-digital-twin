
# Create your models here.
from django.db import models


class Service(models.Model):
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class Region(models.Model):
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100, default="India")
    level = models.CharField(max_length=50)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = "regions"
        managed = False

    def __str__(self):
        return f"{self.name} - {self.level}"
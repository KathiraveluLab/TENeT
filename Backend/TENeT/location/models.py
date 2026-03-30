from django.contrib.gis.db import models

class HealthCenterData(models.Model):
    name = models.CharField(max_length=100,null=True)
    location = models.PointField(null=True)
class InternetData(models.Model):
    frn = models.CharField(max_length=80, null=True, blank=True)
    providerid = models.BigIntegerField(null=True, blank=True)
    brandname = models.CharField(max_length=80, null=True, blank=True)
    technology = models.IntegerField(null=True, blank=True)
    mindown = models.FloatField(null=True, blank=True)
    minup = models.FloatField(null=True, blank=True)
    minsignal = models.IntegerField(null=True, blank=True)
    environmnt = models.IntegerField(null=True, blank=True)
    h3_res9_id = models.CharField(max_length=80, null=True, blank=True)
    mpoly = models.MultiPolygonField(srid=4326,null=True)

    def __str__(self):
        return f"{self.brandname} - {self.h3_res9_id}"
    

# Create your models here.

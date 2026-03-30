from django.db import models
from django.core.exceptions import ValidationError
class Metadata(models.Model):
    lastupdated = models.CharField()
    def save(self, *args, **kwargs):
        if not self.pk and Metadata.objects.exists():
            raise ValidationError("There can be only one Metadata instance.")
        return super(Metadata, self).save(*args, **kwargs)
# Create your models here.

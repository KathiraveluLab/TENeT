from django.contrib import admin
from .models import HealthCenterData
from .models import InternetData
admin.site.register([HealthCenterData,InternetData])
# Register your models here.

from django.shortcuts import render
from .models import Metadata

def updateMetadata(lastupdate):
    Metadata.objects.update_or_create(id='1',lastupdated=lastupdate)
def getLastupdate():
    try:
        obj = Metadata.objects.get(id = '1')
        return obj.lastupdated
    except Exception as e:
        return None
# Create your views here.

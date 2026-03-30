from rest_framework.decorators import api_view
from rest_framework.response import Response
from .logic import get_health_data, get_internet_data, calculateScore
@api_view(['GET'])
def get_tenet_data(request):
    internet_data = get_internet_data()
    health_data = get_health_data()
    return Response({
        "internet": internet_data,
        "health": health_data
    })
@api_view(['POST'])
def calculate(request):
    longtiude = request.data.get("longtiude")
    latitiude = request.data.get("latitiude")
    radius = request.data.get("MapRadius")
    res = calculateScore(latitiude,longtiude,radius)
    return Response({
        "result":res
    })
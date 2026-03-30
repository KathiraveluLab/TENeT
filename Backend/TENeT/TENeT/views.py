from rest_framework.decorators import api_view
from rest_framework.response import Response
from .logic import get_health_data
@api_view(['GET'])
def get_tenet_data(request):
    # internet_data = get_internet_data()
    health_data = get_health_data()
    print(health_data)
    return Response({
        "internet": [61.0, -150.0, 64.0, -145.0],
        "health": health_data
    })
# def coverage_view(request):
#     gdf = get_internet_data()

#     geojson = gdf.to_json()

#     return Response(geojson)
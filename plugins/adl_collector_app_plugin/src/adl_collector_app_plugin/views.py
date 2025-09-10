from adl.api.serializers import StationLinkSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import ManualObservationStationLink


@api_view(['GET'])
def get_observer_station_links(request):
    user = request.user
    station_links = ManualObservationStationLink.objects.filter(observers__user=user)
    data = StationLinkSerializer(station_links, many=True).data
    return Response(data)

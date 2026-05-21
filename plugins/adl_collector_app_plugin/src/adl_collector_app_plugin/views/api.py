from django.db import transaction
from rest_framework import status, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import ManualObservationStationLink, CollectorSubmission
from ..serializers import (
    ObserverStationLinkListSerializer,
    ObserverStationLinkDetailSerializer,
    SubmissionInSer,
)
from ..utils import compute_submission_hash


@api_view(['GET'])
def get_observer_station_links(request):
    user = request.user
    
    station_links = ManualObservationStationLink.objects.filter(
        enabled=True,
        observers__user=user,
        observers__enabled=True).distinct()
    
    data = ObserverStationLinkListSerializer(station_links, many=True).data
    return Response(data)


@api_view(['GET'])
def get_station_link(request, station_link_id):
    user = request.user
    try:
        station_link = ManualObservationStationLink.objects.get(id=station_link_id, observers__user=user)
    except ManualObservationStationLink.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=404)
    data = ObserverStationLinkDetailSerializer(station_link).data
    return Response(data)


class SubmitManualObservation(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serialized = SubmissionInSer(data=request.data, context={"request": request})
        serialized.is_valid(raise_exception=True)
        
        station_link = serialized.validated_data["_station_link"]
        obs_time = serialized.validated_data["observation_time"]
        meta = serialized.validated_data.get("meta") or {}
        records = serialized.validated_data["records"]
        
        chash = compute_submission_hash(
            station_link_id=station_link.id,
            observation_time=obs_time,
            records=records,
            meta=meta,
        )
        
        existing = CollectorSubmission.objects.filter(
            observer=serialized.validated_data["_observer"],
            observation_time=obs_time,
            content_hash=chash,
        ).first()
        
        if existing:
            return Response(
                {
                    "station_link_id": station_link.id,
                    "status": "accepted",
                    "idempotent": True,
                    "id": existing.pk,
                    "observation_time": existing.observation_time,
                    "is_test_submission": existing.is_test_submission,
                },
                status=status.HTTP_200_OK,
            )
        
        with transaction.atomic():
            submission = serialized.save()
        
        return Response(
            {
                "station_link_id": station_link.id,
                "status": "accepted",
                "idempotent": False,
                "id": submission.pk,
                "observation_time": submission.observation_time,
                "is_test_submission": submission.is_test_submission,
            },
            status=status.HTTP_201_CREATED,
        )

from django.db import transaction
from rest_framework import status, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ManualObservationStationLink, CollectorSubmission
from .serializers import ObserverStationLinkListSerializer, ObserverStationLinkDetailSerializer, SubmissionInSer
from .utils import compute_submission_hash


@api_view(['GET'])
def get_observer_station_links(request):
    user = request.user
    
    # Only return station links where the user is an enabled observer
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
    permission_classes = [permissions.IsAuthenticated]  # add your scope checker if needed
    
    def post(self, request):
        ser = SubmissionInSer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        
        sl = ser.validated_data["_station_link"]
        obs_time = ser.validated_data["observation_time"]
        meta = ser.validated_data.get("meta") or {}
        records = ser.validated_data["records"]
        idem_key = ser.validated_data.get("idempotency_key", "")
        
        # Deterministic content hash for idempotency
        chash = compute_submission_hash(
            station_link_id=sl.id,
            observation_time=obs_time,
            records=records,
            meta=meta,
        )
        
        # Short-circuit if same payload was already stored
        existing = CollectorSubmission.objects.filter(
            observer=ser.validated_data["_observer"],
            observation_time=obs_time,
            content_hash=chash,
        ).first()
        
        if existing:
            return Response(
                {"status": "ok", "idempotent": True, "submission_id": existing.pk},
                status=status.HTTP_200_OK,
            )
        
        with transaction.atomic():
            sub = ser.save()  # creates CollectorSubmission + N CollectorSubmissionRecord
        
        return Response(
            {"status": "ok", "submission_id": sub.pk},
            status=status.HTTP_201_CREATED,
        )

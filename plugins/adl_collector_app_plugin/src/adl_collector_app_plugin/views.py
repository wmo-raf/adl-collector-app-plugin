from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import render
from rest_framework import status, permissions
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ManualObservationStationLink, CollectorSubmission, CollectorSubmissionRecord
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
        serialized = SubmissionInSer(data=request.data, context={"request": request})
        serialized.is_valid(raise_exception=True)
        
        station_link = serialized.validated_data["_station_link"]
        obs_time = serialized.validated_data["observation_time"]
        meta = serialized.validated_data.get("meta") or {}
        records = serialized.validated_data["records"]
        idem_key = serialized.validated_data.get("idempotency_key", "")
        
        # Deterministic content hash for idempotency
        chash = compute_submission_hash(
            station_link_id=station_link.id,
            observation_time=obs_time,
            records=records,
            meta=meta,
        )
        
        # Short-circuit if same payload was already stored
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
            submission = serialized.save()  # creates CollectorSubmission + N CollectorSubmissionRecord
        
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


def view_test_collector_submissions(request):
    submissions = (
        CollectorSubmission.objects
        .filter(is_test_submission=True)
        .select_related("observer__user", "station_link")
        .prefetch_related(
            Prefetch(
                "records",
                queryset=CollectorSubmissionRecord.objects.select_related("variable_mapping"),
            )
        )
        .order_by("-created_at")[:100]
    )
    
    context = {
        "submissions": submissions,
        "page_title": "Test Collector Submissions",
    }
    
    return render(
        request,
        "adl_collector_app_plugin/test_submissions.html",
        context
    )

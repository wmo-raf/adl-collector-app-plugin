from django.utils import timezone as dj_timezone
from rest_framework import serializers

from .base import AwareDateTimeField
from ..models import (
    ManualObservationStationLink,
    ManualObservationStationLinkVariableMapping,
    ManualObservationStationLinkObserver,
    CollectorSubmission,
    CollectorSubmissionRecord,
)
from ..utils import compute_submission_hash


class SubmissionRecordInSer(serializers.Serializer):
    variable_mapping_id = serializers.IntegerField()
    value = serializers.FloatField()


class SubmissionInSer(serializers.Serializer):
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)
    submission_time = AwareDateTimeField()
    observation_time = AwareDateTimeField()
    station_link_id = serializers.IntegerField()
    records = SubmissionRecordInSer(many=True)
    is_test_submission = serializers.BooleanField(required=False, default=False)
    meta = serializers.DictField(required=False)

    def validate(self, data):
        request = self.context["request"]
        user = request.user

        try:
            sl: ManualObservationStationLink = ManualObservationStationLink.objects.get(pk=data["station_link_id"])
        except ManualObservationStationLink.DoesNotExist:
            raise serializers.ValidationError("Invalid station_link_id.")

        try:
            observer = ManualObservationStationLinkObserver.objects.select_related("station_link").get(
                station_link_id=sl.id, user=user, enabled=True
            )
        except ManualObservationStationLinkObserver.DoesNotExist:
            raise serializers.ValidationError("User is not an enabled observer for this station link.")

        submission_time = data["submission_time"]

        if submission_time > dj_timezone.now():
            raise serializers.ValidationError("submission_time cannot be in the future.")

        # All variable mappings must belong to this station link and be direct-entry eligible
        ids = [r["variable_mapping_id"] for r in data["records"]]
        vmaps = list(
            ManualObservationStationLinkVariableMapping.objects.select_related(
                "station_link", "adl_parameter", "obs_parameter_unit"
            ).filter(id__in=ids, station_link_id=sl.id, show_in_direct_entry=True)
        )
        if len(vmaps) != len(ids):
            raise serializers.ValidationError(
                "One or more variable_mapping_id values are invalid or not available for direct entry.")

        data["_station_link"] = sl
        data["_observer"] = observer
        data["_vmaps_by_id"] = {vm.id: vm for vm in vmaps}
        return data

    def create(self, validated):
        sl = validated["_station_link"]
        observer = validated["_observer"]
        payload = self.initial_data
        meta = validated.get("meta") or {}

        chash = compute_submission_hash(
            station_link_id=sl.id,
            observation_time=validated["observation_time"],
            records=validated["records"],
            meta=meta,
        )

        sub = CollectorSubmission.objects.create(
            station_link=sl,
            observer=observer,
            submission_time=validated["submission_time"],
            observation_time=validated["observation_time"],
            is_test_submission=validated["is_test_submission"],
            data=payload,
            idempotency_key=validated.get("idempotency_key", ""),
            content_hash=chash,
        )

        recs = [
            CollectorSubmissionRecord(
                submission=sub,
                variable_mapping=validated["_vmaps_by_id"][r["variable_mapping_id"]],
                value=r["value"],
            )
            for r in validated["records"]
        ]
        CollectorSubmissionRecord.objects.bulk_create(recs)
        return sub

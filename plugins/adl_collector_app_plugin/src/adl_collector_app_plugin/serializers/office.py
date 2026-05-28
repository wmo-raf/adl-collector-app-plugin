from django.utils import timezone as dj_timezone
from rest_framework import serializers

from .base import AwareDateTimeField
from ..models import (
    ManualObservationStationLink,
    ManualObservationStationLinkVariableMapping,
    CollectorSubmission,
    CollectorSubmissionRecord,
)
from ..utils import compute_submission_hash


class OfficeSubmissionRecordInSer(serializers.Serializer):
    variable_mapping_id = serializers.IntegerField()
    value = serializers.FloatField()


class OfficeSubmissionInSer(serializers.Serializer):
    """
    Accepts a direct-parameter submission from an office staff user.
    Auth: Django session (Wagtail admin login), not observer token.
    """
    station_link_id = serializers.IntegerField()
    observation_time = AwareDateTimeField()
    records = OfficeSubmissionRecordInSer(many=True, min_length=1)

    def validate(self, data):
        try:
            sl = ManualObservationStationLink.objects.get(pk=data["station_link_id"])
        except ManualObservationStationLink.DoesNotExist:
            raise serializers.ValidationError("Invalid station_link_id.")

        if data["observation_time"] > dj_timezone.now():
            raise serializers.ValidationError("observation_time cannot be in the future.")

        ids = [r["variable_mapping_id"] for r in data["records"]]
        vmaps = list(
            ManualObservationStationLinkVariableMapping.objects.select_related(
                "adl_parameter", "obs_parameter_unit"
            ).filter(id__in=ids, station_link_id=sl.id)
        )
        if len(vmaps) != len(ids):
            raise serializers.ValidationError(
                "One or more variable_mapping_id values are invalid for this station link."
            )

        data["_station_link"] = sl
        data["_vmaps_by_id"] = {vm.id: vm for vm in vmaps}
        return data

    def create(self, validated):
        from django.utils import timezone as tz
        sl = validated["_station_link"]
        staff_user = self.context["request"].user
        obs_time = validated["observation_time"]
        now = tz.now()

        chash = compute_submission_hash(
            station_link_id=sl.id,
            observation_time=obs_time,
            records=validated["records"],
            meta={},
        )

        existing = CollectorSubmission.objects.filter(
            office_submitted_by=staff_user,
            observation_time=obs_time,
            content_hash=chash,
        ).first()
        if existing:
            return existing, True

        sub = CollectorSubmission.objects.create(
            station_link=sl,
            office_submitted_by=staff_user,
            submission_time=now,
            observation_time=obs_time,
            data=self.initial_data,
            idempotency_key="",
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
        return sub, False

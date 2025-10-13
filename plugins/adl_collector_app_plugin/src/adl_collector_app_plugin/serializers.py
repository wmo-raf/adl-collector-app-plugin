import re
from datetime import timezone
from zoneinfo import ZoneInfo

from adl.api.serializers import ReadOnlyModelSerializer
from adl.core.models import DataParameter
from django.utils import timezone as dj_timezone
from rest_framework import serializers

from .models import (
    ManualObservationStationLinkVariableMapping,
    ManualObservationStationLink,
    ManualObservationStationLinkObserver,
    CollectorSubmission,
    CollectorSubmissionRecord,
)
from .utils import compute_submission_hash


class ObserverStationLinkListSerializer(ReadOnlyModelSerializer):
    name = serializers.CharField(source="station.name")
    
    class Meta:
        model = ManualObservationStationLink
        fields = ("id", "name")


class DataParameterSerializer(ReadOnlyModelSerializer):
    class Meta:
        model = DataParameter
        fields = ("id", "name")


class ManualObservationStationLinkVariableMappingSerializer(ReadOnlyModelSerializer):
    obs_parameter_unit = serializers.CharField(source="obs_parameter_unit.name")
    adl_parameter_name = serializers.CharField(source="adl_parameter.name")
    range_check = serializers.SerializerMethodField()
    
    class Meta:
        model = ManualObservationStationLinkVariableMapping
        fields = ("id", "adl_parameter_name", "obs_parameter_unit", "is_rainfall", "range_check",)
    
    def get_range_check(self, obj):
        if not obj.qc_checks:
            return None
        
        for block in obj.qc_checks:
            if block.block_type == "range_check":
                block_value = block.value
                return {
                    "min": block_value.get("min_value"),
                    "max": block_value.get("max_value"),
                    "inclusive": block_value.get("inclusive_bounds", True),
                }
        
        return None


class ObserverStationLinkDetailSerializer(ReadOnlyModelSerializer):
    name = serializers.CharField(source="station.name")
    variable_mappings = ManualObservationStationLinkVariableMappingSerializer(many=True)
    schedule = serializers.SerializerMethodField()
    timezone = serializers.SerializerMethodField()
    
    class Meta:
        model = ManualObservationStationLink
        fields = ("id", "name", "timezone", "variable_mappings", "schedule",)
    
    def get_timezone(self, obj):
        # assuming obj.timezone is a ZoneInfo instance
        if isinstance(obj.timezone, ZoneInfo):
            return obj.timezone.key
        return None
    
    def get_schedule(self, obj):
        sv = obj.schedule
        if not sv or len(sv) == 0:
            return None
        
        # you constrained min_num=max_num=1, so take the first block
        child = sv[0]  # StreamChild
        block = child.block
        
        # Prefer API representation if the block defines it; otherwise fall back to prep value
        if hasattr(block, "get_api_representation"):
            config = block.get_api_representation(child.value)
        else:
            config = block.get_prep_value(child.value)
        
        return {
            "mode": child.block_type,  # "fixed_local" | "windowed_only"
            "config": config,  # JSON-serializable
        }


class SubmissionRecordInSer(serializers.Serializer):
    variable_mapping_id = serializers.IntegerField()
    value = serializers.FloatField()


class AwareDateTimeField(serializers.DateTimeField):
    """
    DRF DateTimeField that enforces timezone-awareness.
    - Rejects inputs without 'Z' or +/-HH:MM offset.
    - Converts accepted values to UTC.
    """
    
    _tz_regex = re.compile(r"(Z|[+-]\d{2}:\d{2})$")
    
    def to_internal_value(self, value):
        # If value is a string, ensure it ends with Z or a timezone offset
        if isinstance(value, str):
            if not self._tz_regex.search(value):
                raise serializers.ValidationError(
                    "Datetime must include timezone info (Z or +HH:MM offset)."
                )
        
        dt = super().to_internal_value(value)
        
        # Safety: reject if somehow parsed naive
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise serializers.ValidationError(
                "Datetime must include timezone info (Z or +HH:MM offset)."
            )
        
        return dt.astimezone(timezone.utc)


class SubmissionInSer(serializers.Serializer):
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)
    submission_time = AwareDateTimeField()
    observation_time = AwareDateTimeField()
    station_link_id = serializers.IntegerField()
    records = SubmissionRecordInSer(many=True)
    meta = serializers.DictField(required=False)
    
    def validate(self, data):
        request = self.context["request"]
        user = request.user
        
        # Station link must exist
        try:
            sl: ManualObservationStationLink = ManualObservationStationLink.objects.get(pk=data["station_link_id"])
        except ManualObservationStationLink.DoesNotExist:
            raise serializers.ValidationError("Invalid station_link_id.")
        
        # User must be an enabled observer for this station link
        try:
            observer = ManualObservationStationLinkObserver.objects.select_related("station_link").get(
                station_link_id=sl.id, user=user, enabled=True
            )
        except ManualObservationStationLinkObserver.DoesNotExist:
            raise serializers.ValidationError("User is not an enabled observer for this station link.")
        
        obs_time = data["observation_time"]
        submission_time = data["submission_time"]
        
        # if obs_time > dj_timezone.now():
        #     raise serializers.ValidationError("observation_time cannot be in the future.")
        
        if submission_time > dj_timezone.now():
            raise serializers.ValidationError("submission_time cannot be in the future.")
        
        # All variable mappings must belong to this station link
        ids = [r["variable_mapping_id"] for r in data["records"]]
        vmaps = list(
            ManualObservationStationLinkVariableMapping.objects.select_related(
                "station_link", "adl_parameter", "obs_parameter_unit"
            ).filter(id__in=ids, station_link_id=sl.id)
        )
        if len(vmaps) != len(ids):
            raise serializers.ValidationError(
                "One or more variable_mapping_id values are invalid for this station link.")
        
        data["_station_link"] = sl
        data["_observer"] = observer
        data["_vmaps_by_id"] = {vm.id: vm for vm in vmaps}
        return data
    
    def create(self, validated):
        sl = validated["_station_link"]
        observer = validated["_observer"]
        payload = self.initial_data
        meta = validated.get("meta") or {}
        
        # Compute hash on normalized (UTC + sorted) payload parts
        chash = compute_submission_hash(
            station_link_id=sl.id,
            observation_time=validated["observation_time"],
            records=validated["records"],
            meta=meta,
        )
        
        sub = CollectorSubmission.objects.create(
            station_link=sl,
            observer=observer,
            submission_time=validated["submission_time"],  # stored UTC
            observation_time=validated["observation_time"],  # stored UTC
            data=payload,  # raw payload snapshot
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

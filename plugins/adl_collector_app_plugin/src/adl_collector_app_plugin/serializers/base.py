import re
from zoneinfo import ZoneInfo

from adl.api.serializers import ReadOnlyModelSerializer
from adl.core.models import DataParameter
from rest_framework import serializers

from ..models import (
    ManualObservationStationLink,
    ManualObservationStationLinkVariableMapping,
)


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
    variable_mappings = serializers.SerializerMethodField()
    schedule = serializers.SerializerMethodField()
    timezone = serializers.SerializerMethodField()
    
    def get_variable_mappings(self, obj):
        qs = obj.variable_mappings.filter(show_in_direct_entry=True)
        return ManualObservationStationLinkVariableMappingSerializer(qs, many=True).data
    
    class Meta:
        model = ManualObservationStationLink
        fields = ("id", "name", "timezone", "variable_mappings", "schedule",)
    
    def get_timezone(self, obj):
        if isinstance(obj.timezone, ZoneInfo):
            return obj.timezone.key
        return None
    
    def get_schedule(self, obj):
        sv = obj.schedule
        if not sv or len(sv) == 0:
            return None
        
        child = sv[0]  # StreamChild
        block = child.block
        
        if hasattr(block, "get_api_representation"):
            config = block.get_api_representation(child.value)
        else:
            config = block.get_prep_value(child.value)
        
        return {
            "mode": child.block_type,  # "fixed_local" | "windowed_only"
            "config": config,
        }


class AwareDateTimeField(serializers.DateTimeField):
    """
    DRF DateTimeField that enforces timezone-awareness.
    - Rejects inputs without 'Z' or +/-HH:MM offset.
    - Converts accepted values to UTC.
    """
    
    _tz_regex = re.compile(r"(Z|[+-]\d{2}:\d{2})$")
    
    def to_internal_value(self, value):
        if isinstance(value, str):
            if not self._tz_regex.search(value):
                raise serializers.ValidationError(
                    "Datetime must include timezone info (Z or +HH:MM offset)."
                )
        
        dt = super().to_internal_value(value)
        
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise serializers.ValidationError(
                "Datetime must include timezone info (Z or +HH:MM offset)."
            )
        
        from datetime import timezone
        return dt.astimezone(timezone.utc)

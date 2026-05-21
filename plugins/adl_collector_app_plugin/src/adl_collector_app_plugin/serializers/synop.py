from datetime import timezone, datetime

from django.db import transaction
from django.utils import timezone as dj_timezone
from rest_framework import serializers

from adl.api.serializers import ReadOnlyModelSerializer

from ..models import (
    ManualObservationStationLink,
    ManualObservationStationLinkVariableMapping,
    ManualObservationStationLinkObserver,
    CollectorSubmission,
    CollectorSubmissionRecord,
    SynopParameterMapping,
    SynopMessage,
)
from ..synop_utils import decode_fm12, build_submission_records_from_synop
from ..utils import compute_submission_hash


class SynopParameterMappingSerializer(ReadOnlyModelSerializer):
    adl_parameter_name = serializers.CharField(source="adl_parameter.name")
    source_unit_name = serializers.CharField(source="source_unit.name")

    class Meta:
        model = SynopParameterMapping
        fields = ("id", "adl_parameter_name", "fm12_element_path", "source_unit_name")


class SynopDecodeInSer(serializers.Serializer):
    """Used for the decode-preview endpoint — does not persist anything."""
    station_link_id = serializers.IntegerField()
    raw_message = serializers.CharField()

    def validate(self, data):
        try:
            sl = ManualObservationStationLink.objects.select_related(
                "network_connection"
            ).get(pk=data["station_link_id"])
        except ManualObservationStationLink.DoesNotExist:
            raise serializers.ValidationError("Invalid station_link_id.")

        try:
            decoded = decode_fm12(data["raw_message"])
        except (ValueError, ImportError) as exc:
            raise serializers.ValidationError(f"Could not decode SYNOP: {exc}")

        mappings = list(
            SynopParameterMapping.objects.select_related("adl_parameter", "source_unit").all()
        )

        data["_station_link"] = sl
        data["_decoded"] = decoded
        data["_mappings"] = mappings
        return data


class SynopSubmitInSer(serializers.Serializer):
    """Persists a SYNOP message and creates a CollectorSubmission from decoded values."""
    observation_year = serializers.IntegerField()
    observation_month = serializers.IntegerField()
    raw_message = serializers.CharField()

    def validate(self, data):
        request = self.context["request"]

        try:
            decoded = decode_fm12(data["raw_message"])
        except (ValueError, ImportError) as exc:
            raise serializers.ValidationError(f"Could not decode SYNOP: {exc}")

        station_id = decoded.get("station_id", {}).get("value")

        if station_id is None:
            raise serializers.ValidationError("No station_id found in SYNOP message.")

        try:
            sl = ManualObservationStationLink.objects.select_related(
                "network_connection"
            ).get(station__wsi_local=station_id)
        except ManualObservationStationLink.DoesNotExist:
            raise serializers.ValidationError(f"No station link found for SYNOP station_id {station_id}.")

        mappings = list(
            SynopParameterMapping.objects.select_related("adl_parameter", "source_unit").all()
        )

        if not mappings:
            raise serializers.ValidationError("No SYNOP parameter mapping found.")

        obs_time_info = decoded.get("obs_time") or {}
        day_info = obs_time_info.get("day") or {}
        hour_info = obs_time_info.get("hour") or {}
        day = day_info.get("value")
        hour = hour_info.get("value")
        if day is None:
            raise serializers.ValidationError("No day found in SYNOP message.")
        if hour is None:
            raise serializers.ValidationError("No hour found in SYNOP message.")

        obs_time = datetime(
            year=data["observation_year"],
            month=data["observation_month"],
            day=day,
            hour=hour,
            minute=0,
            second=0,
            tzinfo=timezone.utc,
        )

        if obs_time > dj_timezone.now():
            raise serializers.ValidationError(
                f"Observation time can not be in the future. Decoded Observation Time: {obs_time.isoformat()}"
            )

        data["_station_link"] = sl
        data["_decoded"] = decoded
        data["_mappings"] = mappings
        data["_obs_time"] = obs_time
        data["_user"] = request.user
        return data

    def create(self, validated):
        sl = validated["_station_link"]
        decoded = validated["_decoded"]
        mappings = validated["_mappings"]
        obs_time = validated["_obs_time"]
        user = validated["_user"]
        now = dj_timezone.now()
        raw = validated["raw_message"]

        mapped_records = build_submission_records_from_synop(decoded, mappings)

        with transaction.atomic():
            synop_msg = SynopMessage.objects.create(
                station_link=sl,
                submitted_by=user,
                observation_time=obs_time,
                raw_message=raw,
                decoded_json=decoded,
            )

            if mapped_records:
                submission_records = [
                    {"variable_mapping_id": _get_variable_mapping_id(sl, r["adl_parameter_id"]), "value": r["value"]}
                    for r in mapped_records
                    if _get_variable_mapping_id(sl, r["adl_parameter_id"]) is not None
                ]

                if submission_records:
                    chash = compute_submission_hash(
                        station_link_id=sl.id,
                        observation_time=obs_time,
                        records=submission_records,
                        meta={"synop": True},
                    )

                    existing = CollectorSubmission.objects.filter(
                        station_link=sl,
                        observation_time=obs_time,
                        content_hash=chash,
                    ).first()

                    if not existing:
                        vmaps = {
                            vm.adl_parameter_id: vm
                            for vm in ManualObservationStationLinkVariableMapping.objects.filter(
                                station_link=sl,
                                adl_parameter_id__in=[r["adl_parameter_id"] for r in mapped_records],
                            )
                        }

                        sub = CollectorSubmission.objects.create(
                            station_link=sl,
                            office_submitted_by=user if not _is_observer(sl, user) else None,
                            observer=_get_observer(sl, user),
                            submission_time=now,
                            observation_time=obs_time,
                            data={"synop_message_id": synop_msg.id, "raw_message": raw},
                            idempotency_key="",
                            content_hash=chash,
                        )

                        # Deduplicate by variable_mapping_id: if two FM12 paths decode to
                        # the same adl_parameter, keep only the first decoded value to
                        # avoid violating the unique_mapping_per_submission constraint.
                        recs_by_vm_id = {}
                        for r in mapped_records:
                            vm = vmaps.get(r["adl_parameter_id"])
                            if vm and vm.id not in recs_by_vm_id:
                                recs_by_vm_id[vm.id] = CollectorSubmissionRecord(
                                    submission=sub,
                                    variable_mapping=vm,
                                    value=r["value"],
                                )
                        CollectorSubmissionRecord.objects.bulk_create(recs_by_vm_id.values())

                        synop_msg.submission = sub
                        synop_msg.save(update_fields=["submission"])

        return synop_msg


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_variable_mapping_id(station_link, adl_parameter_id):
    """Return the ManualObservationStationLinkVariableMapping id for a given adl_parameter."""
    try:
        return ManualObservationStationLinkVariableMapping.objects.get(
            station_link=station_link,
            adl_parameter_id=adl_parameter_id,
        ).id
    except ManualObservationStationLinkVariableMapping.DoesNotExist:
        return None


def _is_observer(station_link, user) -> bool:
    return ManualObservationStationLinkObserver.objects.filter(
        station_link=station_link, user=user, enabled=True
    ).exists()


def _get_observer(station_link, user):
    return ManualObservationStationLinkObserver.objects.filter(
        station_link=station_link, user=user, enabled=True
    ).first()

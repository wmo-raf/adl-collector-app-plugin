import datetime
import logging
from collections import defaultdict
from typing import List, Any

from adl.core.models import DataParameter
from adl.core.registries import Plugin
from django.db.models import Q
from django.urls import path, include
from django.utils import timezone as dj_timezone

from .models import (
    CollectorSubmissionRecord,
    ManualObservationStationLink,
    ManualObservationStationLinkVariableMapping,
)

logger = logging.getLogger(__name__)


class ADLCollectorPlugin(Plugin):
    type = "adl_collector_app_plugin"
    label = "ADL Collector App Plugin"
    
    def get_urls(self):
        return [
            path("api/adl-collector/", include('adl_collector_app_plugin.urls', namespace="adl_collector_app")),
        ]
    
    def after_save_records(self, station_link, station_records: List[Any], saved_records: List[Any]) -> None:
        raw_station_records_by_time = {}
        for rec in station_records:
            t = rec.get("observation_time")
            t_utc = dj_timezone.localtime(t, datetime.timezone.utc)
            submission_id = rec.get("submission_id")
            if t is not None and submission_id is not None:
                raw_station_records_by_time[t_utc.isoformat()] = rec
        
        if not raw_station_records_by_time:
            return
        
        saved_records_by_time = {}
        for rec in saved_records:
            t = rec.time
            t_utc = dj_timezone.localtime(t, datetime.timezone.utc)
            if t is not None:
                saved_records_by_time[t_utc.isoformat()] = rec
        
        # Match saved records to raw records by observation_time
        for t_str, saved_record in saved_records_by_time.items():
            raw_record = raw_station_records_by_time.get(t_str)
            if raw_record is None:
                continue
            
            submission_id = raw_record.get("submission_id")
            if submission_id is None:
                continue
            
            param = saved_record.parameter
            
            # Mark all CollectorSubmissionRecord rows for this submission as processed
            updated_count = (
                CollectorSubmissionRecord.objects
                .filter(submission_id=submission_id, variable_mapping__adl_parameter=param, is_processed=False)
                .update(is_processed=True)
            )
            
            logger.debug(
                "ADLCollectorPlugin.after_save_records: Marked %d CollectorSubmissionRecord rows as processed for submission_id=%s",
                updated_count, submission_id
            )
    
    def get_station_data(self, station_link: ManualObservationStationLink, start_date=None, end_date=None):
        """
        Return a list[dict] where each dict is:
          {
            "observation_time": <datetime>,
            "<adl_parameter_id>": <value>, ...
          }

        Source: unprocessed CollectorSubmissionRecord rows associated with this station_link,
        grouped by submission.observation_time.
        """
        
        # Build time filter on the submission.observation_time
        time_q = Q()
        if start_date is not None:
            time_q &= Q(submission__observation_time__gte=start_date)
        if end_date is not None:
            time_q &= Q(submission__observation_time__lt=end_date)
        
        # Pull unprocessed and not-testing rows for this link
        qs = (
            CollectorSubmissionRecord.objects
            .select_related(
                "submission",
                "submission__station_link",
                "variable_mapping__adl_parameter",
                "variable_mapping__obs_parameter_unit",
            )
            .filter(
                submission__station_link=station_link,
                submission__is_test_submission=False,
                is_processed=False,
            )
            .filter(time_q)
            .order_by("submission__observation_time", "pk")
        )
        
        # Group by observation_time → {str(param_id): value}
        grouped: dict[datetime.datetime, dict] = defaultdict(dict)
        
        for rec in qs:
            sub = rec.submission
            vm: ManualObservationStationLinkVariableMapping = rec.variable_mapping
            param: DataParameter = vm.adl_parameter
            
            t = sub.observation_time
            parcel = grouped[t]
            # ensure observation_time present
            if "observation_time" not in parcel:
                parcel["observation_time"] = t
            
            if "submission_id" not in parcel:
                parcel["submission_id"] = sub.id
            
            # keys as strings
            parcel[str(param.id)] = rec.value
        
        # Return a list
        records = list(grouped.values())
        logger.debug(
            "ManualObservationPlugin.get_station_data: link=%s start=%s end=%s -> %d records",
            station_link.id, start_date, end_date, len(records)
        )
        
        return records

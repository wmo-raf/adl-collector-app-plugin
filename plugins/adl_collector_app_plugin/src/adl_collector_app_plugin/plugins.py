import datetime
import logging
from collections import defaultdict
from typing import List, Any

from adl.core.models import DataParameter
from adl.core.registries import Plugin
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
    
    def after_save_records(
            self,
            station_link,
            station_records: List[Any],
            saved_records: List[Any],
            qc_fail_results=None,
    ) -> None:
        """
        Called by the core after each chunk of ObservationRecords is upserted.
        Marks all CollectorSubmissionRecord rows whose submission_id appears in
        this chunk as processed.
        """
        if not station_records:
            return
        
        submission_ids = {
            rec["submission_id"]
            for rec in station_records
            if rec.get("submission_id") is not None
        }
        if not submission_ids:
            return
        
        now = dj_timezone.now()
        updated_count = (
            CollectorSubmissionRecord.objects
            .filter(submission_id__in=submission_ids, is_processed=False)
            .update(is_processed=True, processed_at=now)
        )
        
        logger.debug(
            "ADLCollectorPlugin.after_save_records: marked %d CollectorSubmissionRecord "
            "row(s) as processed for station_link pk=%s (submission_ids=%s)",
            updated_count, station_link.pk, submission_ids,
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

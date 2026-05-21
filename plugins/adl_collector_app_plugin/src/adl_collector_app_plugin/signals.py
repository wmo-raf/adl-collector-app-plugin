import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CollectorSubmission, ManualObservationStationLink

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ManualObservationStationLink)
def auto_sync_synop_mappings(sender, instance, created, **kwargs):
    """
    When a new ManualObservationStationLink is created, automatically create
    ManualObservationStationLinkVariableMapping rows for every existing global
    SynopParameterMapping so the station is ready for SYNOP ingestion immediately.
    """
    if not created:
        return
    
    from .synop_utils import sync_synop_mappings_for_station
    
    try:
        count = sync_synop_mappings_for_station(instance)
        if count:
            logger.info(
                "Auto-synced %d SYNOP variable mapping(s) for new station link %s (pk=%s).",
                count,
                instance.station,
                instance.pk,
            )
    except Exception:
        logger.exception(
            "Failed to auto-sync SYNOP variable mappings for station link pk=%s.", instance.pk
        )


@receiver(post_save, sender=CollectorSubmission)
def trigger_ingestion_on_submission(sender, instance, created, **kwargs):
    """
    Immediately queue ingestion for a new non-test submission so records
    appear in ObservationRecord without waiting for the next Celery Beat tick.

    Uses transaction.on_commit() so the task is queued only after the full
    DB transaction (submission + all CollectorSubmissionRecord rows) is committed,
    preventing the Celery worker from reading rows that don't yet exist.
    """
    if not created or instance.is_test_submission:
        return
    
    conn_id = instance.station_link.network_connection_id
    sl_id = instance.station_link_id
    
    def _queue():
        try:
            from adl.core.tasks import process_station_link_batch
            
            process_station_link_batch.delay(conn_id, [sl_id])
            logger.debug(
                "Queued immediate ingestion for station_link pk=%s after submission pk=%s.",
                sl_id,
                instance.pk,
            )
        except Exception:
            logger.exception(
                "Failed to queue immediate ingestion for submission pk=%s.", instance.pk
            )
    
    transaction.on_commit(_queue)

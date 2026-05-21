from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import InlinePanel, FieldPanel
from wagtail.models import Orderable
from wagtail.snippets.models import register_snippet

from .station_link import (
    ManualObservationStationLink,
    ManualObservationStationLinkVariableMapping,
    ManualObservationStationLinkObserver,
)


@register_snippet
class CollectorSubmission(ClusterableModel):
    station_link = models.ForeignKey(
        ManualObservationStationLink,
        on_delete=models.PROTECT,
        related_name="submissions",
    )
    
    # Idempotency
    idempotency_key = models.CharField(max_length=128, blank=True, db_index=True)
    content_hash = models.CharField(max_length=64, db_index=True)
    
    # Who submitted — either a mobile/field observer OR an office staff user (but not both)
    observer = models.ForeignKey(
        ManualObservationStationLinkObserver,
        on_delete=models.CASCADE,
        related_name="submissions",
        null=True,
        blank=True,
    )
    office_submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="office_submissions",
        verbose_name=_("Office Submitted By"),
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    submission_time = models.DateTimeField()
    observation_time = models.DateTimeField()
    is_test_submission = models.BooleanField(default=False)
    
    data = models.JSONField()
    
    panels = [
        FieldPanel("station_link"),
        FieldPanel("idempotency_key"),
        FieldPanel("observer"),
        FieldPanel("office_submitted_by"),
        FieldPanel("submission_time"),
        FieldPanel("observation_time"),
        FieldPanel("data"),
        InlinePanel("records", label=_("Processed Records")),
    ]
    
    class Meta:
        indexes = [
            models.Index(fields=["station_link", "observation_time"]),
            models.Index(fields=["content_hash"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["observer", "observation_time", "content_hash"],
                name="uq_obs_time_payload",
                condition=models.Q(observer__isnull=False),
            ),
        ]
    
    def __str__(self):
        if self.observer_id:
            who = self.observer.user.username
        elif self.office_submitted_by_id:
            who = f"{self.office_submitted_by.username} (office)"
        else:
            who = "unknown"
        return f"Submission {self.id} by {who} at {self.submission_time.isoformat()}"
    
    @property
    def submitter(self):
        """Returns the User who submitted, regardless of pathway."""
        if self.observer_id:
            return self.observer.user
        return self.office_submitted_by
    
    def clean(self):
        if self.observer_id is None and self.office_submitted_by_id is None:
            raise ValidationError("Either observer or office_submitted_by must be set.")
        if self.observation_time.tzinfo is None:
            raise ValidationError("observation_time must be timezone-aware (UTC).")
        if self.submission_time.tzinfo is None:
            raise ValidationError("submission_time must be timezone-aware (UTC).")
        if self.observation_time > timezone.now():
            raise ValidationError("observation_time cannot be in the future.")


@register_snippet
class CollectorSubmissionRecord(Orderable):
    submission = ParentalKey(CollectorSubmission, on_delete=models.CASCADE, related_name="records")
    variable_mapping = models.ForeignKey(ManualObservationStationLinkVariableMapping, on_delete=models.CASCADE)
    value = models.FloatField()
    
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    
    class Meta:
        indexes = [
            models.Index(fields=["variable_mapping", "is_processed"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "variable_mapping"],
                name="unique_mapping_per_submission",
            ),
        ]

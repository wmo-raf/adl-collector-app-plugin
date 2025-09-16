from adl.core.models import NetworkConnection, StationLink, DataParameter, Unit
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import InlinePanel, FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Orderable
from wagtail.snippets.models import register_snippet

from adl_collector_app_plugin.blocks import FixedSlotLocalScheduleMode, WindowedOnlyScheduleMode


class ManualObservationConnection(NetworkConnection):
    """
    Model representing a connection for manual observations.
    """
    station_link_model_string_label = "adl_collector_app_plugin.ManualObservationStationLink"
    
    panels = NetworkConnection.panels
    
    class Meta:
        verbose_name = _("Manual Observation Connection")
        verbose_name_plural = _("Manual Observation Connections")


class ManualObservationStationLink(StationLink):
    """
    Model representing a link to a station for manual observations.
    """
    
    schedule = StreamField(
        block_types=[
            ('fixed_local', FixedSlotLocalScheduleMode(label=_("Fixed Slots in Local Time"))),
            ('windowed_only', WindowedOnlyScheduleMode(label=_("Windowed Only"))),
        ],
        min_num=1,
        max_num=1,
        null=True,
        blank=True,
        verbose_name=_("Schedule"),
    )
    
    panels = StationLink.panels + [
        InlinePanel("variable_mappings", label=_("Variable Mappings")),
        InlinePanel("observers", heading=_("Observers"), label=_("Observer")),
        FieldPanel("schedule"),
    ]
    
    class Meta:
        verbose_name = _("Manual Observation Station Link")
        verbose_name_plural = _("Manual Observation Station Links")
    
    def get_variable_mappings(self):
        """
        Returns the variable mappings associated with this station link.
        """
        return self.variable_mappings.all()


class ManualObservationStationLinkVariableMapping(Orderable):
    """
    Model representing a mapping between a station link and a data parameter for manual observations.
    """
    station_link = ParentalKey(ManualObservationStationLink, on_delete=models.CASCADE, related_name="variable_mappings")
    adl_parameter = models.ForeignKey(DataParameter, on_delete=models.CASCADE, verbose_name=_("ADL Parameter"))
    obs_parameter_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name=_("Observation Parameter Unit"))
    is_rainfall = models.BooleanField(verbose_name=_("Is Rainfall"), default=False)
    
    class Meta:
        verbose_name = _("Manual Observation Variable Mapping")
        verbose_name_plural = _("Manual Observation Variable Mappings")
    
    def __str__(self):
        return f"{self.adl_parameter.name} ({self.obs_parameter_unit.name})"
    
    @property
    def source_parameter_name(self):
        """
        Returns the ID of the ADL variable.
        """
        return self.adl_parameter.id
    
    @property
    def source_parameter_unit(self):
        """
        Returns the unit of the observation parameter.
        """
        return self.obs_parameter_unit


class ManualObservationStationLinkObserver(Orderable):
    """
    Model representing an observer for a manual observation station link.
    """
    station_link = ParentalKey(ManualObservationStationLink, on_delete=models.CASCADE, related_name="observers")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        on_delete=models.PROTECT,
    )
    enabled = models.BooleanField(verbose_name=_("Enabled"), default=True)
    
    panels = [
        FieldPanel("user"),
        FieldPanel("enabled"),
    ]
    
    class Meta:
        verbose_name = _("Station Observer")
        verbose_name_plural = _("Station Observers")
    
    def __str__(self):
        return f"{self.user.username} ({'Enabled' if self.enabled else 'Disabled'})"


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
    
    # Who / when
    observer = models.ForeignKey(ManualObservationStationLinkObserver, on_delete=models.CASCADE,
                                 related_name="submissions")
    created_at = models.DateTimeField(auto_now_add=True)
    submission_time = models.DateTimeField()
    observation_time = models.DateTimeField()
    
    # What
    data = models.JSONField()
    
    panels = [
        FieldPanel("station_link"),
        FieldPanel("idempotency_key"),
        FieldPanel("observer"),
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
            # hard idempotency within same observer/time/payload
            models.UniqueConstraint(
                fields=["observer", "observation_time", "content_hash"],
                name="uq_obs_time_payload",
            ),
        ]
    
    def __str__(self):
        return f"Submission {self.id} by {self.observer.user.username} at {self.submission_time.isoformat()}"
    
    def clean(self):
        if self.observation_time.tzinfo is None:
            raise ValidationError("observation_time must be timezone-aware (UTC).")
        if self.submission_time.tzinfo is None:
            raise ValidationError("submission_time must be timezone-aware (UTC).")
        
        # reject absurd future skew (> 1 day by default)
        if self.observation_time > timezone.now():
            raise ValidationError("observation_time cannot be in the future.")


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
            # One record per variable per submission
            models.UniqueConstraint(
                fields=["submission", "variable_mapping"],
                name="unique_mapping_per_submission",
            ),
        ]

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import InlinePanel, FieldPanel
from wagtail.fields import StreamField
from wagtail.models import Orderable

from adl.core.blocks import QCChecksStreamBlock
from adl.core.models import StationLink, DataParameter, Unit

from ..blocks import FixedSlotLocalScheduleMode, WindowedOnlyScheduleMode
from ..validators import validate_start_date


class ManualObservationStationLink(StationLink):
    """
    Model representing a link to a station for manual observations.
    """
    
    start_date = models.DateTimeField(
        blank=True,
        null=True,
        validators=[validate_start_date],
        verbose_name=_("Collection Start Date"),
        help_text=_(
            "Collection never starts before this date. On the first run it is "
            "the start of the backfill; afterwards, moving it forward past the "
            "latest saved record skips the gap. Leave empty to start from the "
            "last hour."
        ),
    )
    
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
        FieldPanel("start_date"),
        InlinePanel("variable_mappings", label=_("Variable Mappings")),
        InlinePanel("observers", heading=_("Observers"), label=_("Observer")),
        FieldPanel("schedule"),
    ]
    
    class Meta:
        verbose_name = _("Manual Observation Station Link")
        verbose_name_plural = _("Manual Observation Station Links")
    
    def get_variable_mappings(self):
        return self.variable_mappings.all()
    
    def get_first_collection_date(self):
        """
        Returns the first collection date for this station link.
        Returns None if no start date is set.
        """
        return self.start_date


class ManualObservationStationLinkVariableMapping(Orderable):
    """
    Model representing a mapping between a station link and a data parameter for manual observations.
    """
    station_link = ParentalKey(ManualObservationStationLink, on_delete=models.CASCADE,
                               related_name="variable_mappings")
    adl_parameter = models.ForeignKey(DataParameter, on_delete=models.CASCADE, verbose_name=_("ADL Parameter"))
    obs_parameter_unit = models.ForeignKey(Unit, on_delete=models.CASCADE,
                                           verbose_name=_("Observation Parameter Unit"))
    is_rainfall = models.BooleanField(verbose_name=_("Is Rainfall"), default=False)
    
    show_in_direct_entry = models.BooleanField(
        default=True,
        verbose_name=_("Show in Direct Entry"),
        help_text=_(
            "If unchecked, this parameter will not appear in office/PWA/app direct-entry forms. "
            "Uncheck for SYNOP-decoded parameters that should not be entered manually."
        ),
    )
    qc_checks = StreamField(
        QCChecksStreamBlock(),
        null=True,
        blank=True,
        verbose_name=_("Quality Control Checks"),
        help_text=_("Configure automatic data quality validation rules for this parameter.")
    )
    
    panels = [
        FieldPanel("adl_parameter"),
        FieldPanel("obs_parameter_unit"),
        FieldPanel("is_rainfall"),
        FieldPanel("show_in_direct_entry"),
        FieldPanel("qc_checks"),
    ]
    
    class Meta:
        verbose_name = _("Manual Observation Variable Mapping")
        verbose_name_plural = _("Manual Observation Variable Mappings")
    
    def __str__(self):
        return f"{self.adl_parameter.name} ({self.obs_parameter_unit.name})"
    
    @property
    def source_parameter_name(self):
        return self.adl_parameter.id
    
    @property
    def source_parameter_unit(self):
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

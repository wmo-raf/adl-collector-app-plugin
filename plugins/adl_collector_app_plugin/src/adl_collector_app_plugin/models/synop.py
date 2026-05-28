from adl.core.models import DataParameter, Unit
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel
from wagtail.snippets.models import register_snippet

from .station_link import ManualObservationStationLink
from .submission import CollectorSubmission
from ..synop_utils import FM12_ELEMENT_PATH_CHOICES


class SynopParameterMapping(models.Model):
    """
    Global mapping from a FM12 SYNOP decoded element path to an ADL DataParameter and source Unit.
    One row per FM12 path for the whole system — not connection-specific.
    """
    adl_parameter = models.OneToOneField(
        DataParameter,
        on_delete=models.CASCADE,
        verbose_name=_("ADL Parameter"),
        help_text=_("Each ADL parameter may only appear in one FM12 mapping."),
        related_name="synop_mapping",
    )
    fm12_element_path = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("FM12 Element Path"),
        choices=FM12_ELEMENT_PATH_CHOICES,
        help_text=_(
            "Dot-notation path into the pymetdecoder decoded dict. "
            "Physical quantities use the '.value' leaf (e.g. 'air_temperature.value'). "
            "Coded WMO parameters use '._code' or '.value' depending on the field "
            "(e.g. 'cloud_cover._code' for oktas, 'cloud_types.low_cloud_type.value' for CL). "
            "For range fields, '._code' is the WMO table index and '.min' is the lower bound in metres."
        ),
    )
    source_unit = models.ForeignKey(
        Unit,
        on_delete=models.CASCADE,
        verbose_name=_("Source Unit"),
        help_text=_("Unit in which pymetdecoder returns this element's value."),
    )
    
    panels = [
        FieldPanel("adl_parameter"),
        FieldPanel("fm12_element_path"),
        FieldPanel("source_unit"),
    ]
    
    class Meta:
        verbose_name = _("SYNOP Parameter Mapping")
        verbose_name_plural = _("SYNOP Parameter Mappings")
    
    def __str__(self):
        return f"{self.adl_parameter.name} ← {self.fm12_element_path}"
    
    @property
    def source_parameter_name(self):
        return self.adl_parameter.id
    
    @property
    def source_parameter_unit(self):
        return self.source_unit


@register_snippet
class SynopMessage(models.Model):
    """
    Archives a raw FM12 SYNOP message alongside its decoded content and the
    CollectorSubmission created from it.
    """
    station_link = models.ForeignKey(
        ManualObservationStationLink,
        on_delete=models.PROTECT,
        related_name="synop_messages",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="synop_messages",
    )
    received_at = models.DateTimeField(auto_now_add=True)
    observation_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Observation time extracted from the SYNOP message or provided by the submitter."),
    )
    raw_message = models.TextField(verbose_name=_("Raw SYNOP Message"))
    decoded_json = models.JSONField(
        verbose_name=_("Decoded SYNOP"),
        help_text=_("Full pymetdecoder output stored for reference."),
    )
    submission = models.OneToOneField(
        CollectorSubmission,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="synop_source",
    )
    
    class Meta:
        indexes = [
            models.Index(fields=["station_link", "observation_time"]),
            models.Index(fields=["received_at"]),
        ]
        verbose_name = _("SYNOP Message")
        verbose_name_plural = _("SYNOP Messages")
    
    def __str__(self):
        return f"SYNOP {self.station_link} @ {self.observation_time or self.received_at}"

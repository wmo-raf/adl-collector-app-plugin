from adl.core.models import NetworkConnection, StationLink, DataParameter, Unit
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import InlinePanel, FieldPanel
from wagtail.models import Orderable


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
    
    panels = StationLink.panels + [
        InlinePanel("variable_mappings", label=_("Variable Mappings")),
        InlinePanel("observers", label=_("Observers")),
    ]
    
    class Meta:
        verbose_name = _("Manual Observation Station Link")
        verbose_name_plural = _("Manual Observation Station Links")


class ManualObservationStationLinkVariableMapping(Orderable):
    """
    Model representing a mapping between a station link and a data parameter for manual observations.
    """
    station_link = ParentalKey(ManualObservationStationLink, on_delete=models.CASCADE, related_name="variable_mappings")
    adl_parameter = models.ForeignKey(DataParameter, on_delete=models.CASCADE, verbose_name=_("ADL Parameter"))
    obs_parameter_unit = models.ForeignKey(Unit, on_delete=models.CASCADE, verbose_name=_("Observation Parameter Unit"))
    
    class Meta:
        verbose_name = _("Manual Observation Variable Mapping")
        verbose_name_plural = _("Manual Observation Variable Mappings")
    
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
        verbose_name=_("Observer"),
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

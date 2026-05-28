from adl.core.models import NetworkConnection
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel


class ManualObservationConnection(NetworkConnection):
    """
    Model representing a connection for manual observations.
    """
    station_link_model_string_label = "adl_collector_app_plugin.ManualObservationStationLink"
    
    enable_office_entry = models.BooleanField(
        default=False,
        verbose_name=_("Enable Office Entry"),
        help_text=_("Show office data entry and SYNOP links for this connection."),
    )
    enable_field_app = models.BooleanField(
        default=False,
        verbose_name=_("Enable Field Observer App"),
        help_text=_("Show the PWA field observer app link for this connection."),
    )
    
    panels = NetworkConnection.panels + [
        FieldPanel("enable_office_entry"),
        FieldPanel("enable_field_app"),
    ]
    
    class Meta:
        verbose_name = _("Manual Observation Connection")
        verbose_name_plural = _("Manual Observation Connections")
    
    def get_extra_model_admin_links(self):
        columns = [
            {
                "label": _("Connection Overview"),
                "url": reverse("collector_connection_overview", args=[self.pk]),
                "icon_name": "home",
                "kwargs": {"attrs": {"target": "_blank"}}
            },
            {
                "label": _("SYNOP Setup Wizard"),
                "url": reverse("synop_setup_wizard") + f"?connection={self.pk}",
                "icon_name": "cog",
                "kwargs": {"attrs": {"target": "_blank"}}
            },
            {
                "label": _("View Test Collector Submissions"),
                "url": reverse("view_test_collector_submissions"),
                "icon_name": "list-ul",
                "kwargs": {"attrs": {"target": "_blank"}}
            },
            {
                "label": _("Monitoring Dashboard"),
                "url": reverse("collector_monitoring") + f"?connection={self.pk}",
                "icon_name": "site",
                "kwargs": {"attrs": {"target": "_blank"}}
            },
        ]
        
        if self.enable_office_entry:
            columns += [
                {
                    "label": _("Office Data Entry"),
                    "url": reverse("collector_office_entry") + f"?connection={self.pk}",
                    "icon_name": "edit",
                    "kwargs": {"attrs": {"target": "_blank"}}
                },
                {
                    "label": _("SYNOP FM12 Entry"),
                    "url": reverse("collector_office_synop") + f"?connection={self.pk}",
                    "icon_name": "doc-full",
                    "kwargs": {"attrs": {"target": "_blank"}}
                },
            ]
        
        if self.enable_field_app:
            columns.append({
                "label": _("Field Observer App"),
                "url": reverse("plugins:collector_field_pwa"),
                "icon_name": "mobile-alt",
                "kwargs": {"attrs": {"target": "_blank"}}
            })
        
        return columns

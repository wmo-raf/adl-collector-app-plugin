from django.conf import settings
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.admin.viewsets.chooser import ChooserViewSet

from .views import (
    view_test_collector_submissions,
    OfficeEntryView,
    OfficeSynopView,
    SynopSetupWizardView,
    StationDetailView,
    connection_overview,
    connection_selector,
    sync_station_synop_mappings_view,
    MonitoringDashboardView,
    TriggerReprocessView,
    MonitoringSubmissionsListView,
    MonitoringSynopListView,
    MonitoringObserversListView,
    MonitoringStationsListView,
)


class UserChooserViewSet(ChooserViewSet):
    model = settings.AUTH_USER_MODEL
    icon = "form"
    choose_one_text = "Choose User"
    choose_another_text = "Choose different User"
    edit_item_text = "Edit this User"
    per_page = 50


@hooks.register("register_admin_viewset")
def register_viewsets():
    return [
        UserChooserViewSet("user_chooser"),
    ]


@hooks.register('register_admin_urls')
def urlconf_adl_collector_app_plugin():
    return [
        path(
            "adl-collector-app-plugin/test-collector-submissions/",
            view_test_collector_submissions,
            name="view_test_collector_submissions",
        ),
        path(
            "adl-collector-app-plugin/office/",
            OfficeEntryView.as_view(),
            name="collector_office_entry",
        ),
        path(
            "adl-collector-app-plugin/office/synop/",
            OfficeSynopView.as_view(),
            name="collector_office_synop",
        ),
        path(
            "adl-collector-app-plugin/monitoring/",
            MonitoringDashboardView.as_view(),
            name="collector_monitoring",
        ),
        path(
            "adl-collector-app-plugin/monitoring/submissions/",
            MonitoringSubmissionsListView.as_view(),
            name="collector_monitoring_submissions",
        ),
        path(
            "adl-collector-app-plugin/monitoring/synop/",
            MonitoringSynopListView.as_view(),
            name="collector_monitoring_synop",
        ),
        path(
            "adl-collector-app-plugin/monitoring/observers/",
            MonitoringObserversListView.as_view(),
            name="collector_monitoring_observers",
        ),
        path(
            "adl-collector-app-plugin/monitoring/stations/",
            MonitoringStationsListView.as_view(),
            name="collector_monitoring_stations",
        ),
        path(
            "adl-collector-app-plugin/monitoring/reprocess/",
            TriggerReprocessView.as_view(),
            name="collector_monitoring_reprocess",
        ),
        path(
            "adl-collector-app-plugin/connections/<int:pk>/",
            connection_overview,
            name="collector_connection_overview",
        ),
        path(
            "adl-collector-app-plugin/synop-setup/",
            SynopSetupWizardView.as_view(),
            name="synop_setup_wizard",
        ),
        path(
            "adl-collector-app-plugin/connections/<int:pk>/sync-synop/",
            sync_station_synop_mappings_view,
            name="collector_sync_synop_mappings",
        ),
        path(
            "adl-collector-app-plugin/connections/<int:pk>/stations/<int:station_pk>/",
            StationDetailView.as_view(),
            name="collector_station_detail",
        ),
        path(
            "adl-collector-app-plugin/connections/",
            connection_selector,
            name="collector_connection_selector",
        ),
    ]


@hooks.register('construct_main_menu')
def build_manual_stations_menu(request, menu_items):
    """
    Adds a 'Manual Stations' top-level menu item (no submenu).
    - Zero connections → item hidden.
    - One connection  → links directly to that connection's overview.
    - Many connections → links to the connection selector page.
    """
    from .models import ManualObservationConnection
    
    connections = list(ManualObservationConnection.objects.only("pk"))
    if not connections:
        return
    
    if len(connections) == 1:
        url = reverse('collector_connection_overview', args=[connections[0].pk])
    else:
        url = reverse('collector_connection_selector')
    
    menu_items.append(
        MenuItem(
            _('Manual Stations'),
            url,
            icon_name='form',
            order=500,
        )
    )

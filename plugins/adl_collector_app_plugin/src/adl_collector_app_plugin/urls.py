from django.urls import path

from .views import (
    get_observer_station_links,
    get_station_link,
    SubmitManualObservation
)

app_name = "adl_collector_app_plugin"

urlpatterns = [
    path("station-link/", get_observer_station_links, name="observer_station_links"),
    path("station-link/<int:station_link_id>/", get_station_link, name="observer_station_link"),
    path("manual-obs/submit/", SubmitManualObservation.as_view(), name="manual_obs_submit"),
]

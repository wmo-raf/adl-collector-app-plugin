from django.urls import path

from .views import get_observer_station_links

app_name = "adl_collector_app_plugin"

urlpatterns = [
    path("observer-station-links/", get_observer_station_links, name="observer_station_links"),
]

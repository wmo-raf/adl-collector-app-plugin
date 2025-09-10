from adl.core.registries import Plugin
from django.urls import path, include


class ADLCollectorPlugin(Plugin):
    type = "adl_collector_app_plugin"
    label = "ADL Collector App Plugin"
    
    def get_urls(self):
        return [
            path("api/adl-collector/", include('adl_collector_app_plugin.urls', namespace="adl_collector_app")),
        ]
    
    def get_station_data(self, station_link, start_date=None, end_date=None):
        return []

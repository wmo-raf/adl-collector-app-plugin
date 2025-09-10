from adl.core.registries import plugin_registry
from django.apps import AppConfig


class PluginNameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = "adl_collector_app_plugin"
    
    def ready(self):
        from .plugins import ADLCollectorPlugin
        
        plugin_registry.register(ADLCollectorPlugin())

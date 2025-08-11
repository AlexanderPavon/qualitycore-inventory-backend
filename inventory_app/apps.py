from django.apps import AppConfig
from django.contrib.auth import get_user_model
import logging

class InventoryAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory_app'

    def ready(self):
        import inventory_app.signals  # noqa

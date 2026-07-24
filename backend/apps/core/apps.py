from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'apps.core'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import apps.core.signals  # noqa

from django.apps import AppConfig


class RBACConfig(AppConfig):
    name = 'apps.rbac'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from .registry import sync_permissions
        try:
            sync_permissions()
        except Exception:
            pass  # DB may not exist yet during migrations

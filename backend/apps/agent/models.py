from django.db import models
from apps.core.models import User


class UserMemory(models.Model):
    """
    Long-term per-user memory: stores preferences and facts learned during conversations.
    Kept in Postgres so it persists across Redis flushes and server restarts.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='memory')
    preferences = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Memory({self.user.email})"

    @classmethod
    def for_user(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj

import uuid
from django.db import models
from apps.core.models import Organization


class TaskRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('dead_letter', 'Dead Letter'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.CharField(max_length=100)
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='task_records',
        null=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payload = models.JSONField(default=dict)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['org', 'status']),
            models.Index(fields=['task_type', 'status']),
            models.Index(fields=['-created_at']),
        ]

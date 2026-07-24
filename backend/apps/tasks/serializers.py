from rest_framework import serializers
from .models import TaskRecord


class TaskRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskRecord
        fields = [
            'id', 'task_type', 'status', 'payload', 'result',
            'error', 'retry_count', 'max_retries',
            'created_at', 'updated_at', 'completed_at',
        ]

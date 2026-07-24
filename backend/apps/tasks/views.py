import json
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.rbac.permissions import HasRBACPermission
from apps.rbac.permissions_registry import Perm, permission_registry
from .models import TaskRecord
from .serializers import TaskRecordSerializer


class TaskListView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("tasks").view]

    def get(self, request):
        qs = TaskRecord.objects.filter(org=request.user.org)
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        serializer = TaskRecordSerializer(qs[:50], many=True)
        return Response(serializer.data)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("tasks").view]

    def get(self, request, task_id):
        try:
            task = TaskRecord.objects.get(id=task_id, org=request.user.org)
        except TaskRecord.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        return Response(TaskRecordSerializer(task).data)


class DeadLetterQueueView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("tasks").view]

    def get(self, request):
        dlq = TaskRecord.objects.filter(
            org=request.user.org, status='dead_letter'
        ).order_by('-updated_at')[:20]
        return Response(TaskRecordSerializer(dlq, many=True).data)


class RetryTaskView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("tasks").edit]

    def post(self, request, task_id):
        try:
            task = TaskRecord.objects.get(
                id=task_id, org=request.user.org, status='dead_letter'
            )
        except TaskRecord.DoesNotExist:
            return Response({'error': 'Dead-letter task not found'}, status=404)

        task.status = 'pending'
        task.retry_count = 0
        task.error = ''
        task.save(update_fields=['status', 'retry_count', 'error', 'updated_at'])

        if task.task_type == 'embed_document':
            from .tasks import embed_document

            embed_document.apply_async(
                kwargs={
                    'document_id': task.payload.get('document_id'),
                    'task_record_id': str(task.id),
                },
                queue='embeddings',
            )

        return Response({'status': 'queued', 'task_id': str(task.id)})


class TaskStreamView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("tasks").view]

    def get(self, request):
        def event_stream():
            import time

            org = request.user.org
            while True:
                tasks = TaskRecord.objects.filter(org=org).order_by('-updated_at')[:10]
                data = TaskRecordSerializer(tasks, many=True).data
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(2)

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.rbac.permissions import HasRBACPermission
from apps.rbac.permissions_registry import Perm, permission_registry
from apps.tasks.models import TaskRecord
from .memory import ShortTermMemory


class ChatView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("agent.chat").view]

    def post(self, request):
        message = request.data.get('message', '').strip()
        if not message:
            return Response({'error': 'message is required'}, status=400)

        session_id = request.data.get('session_id') or str(uuid.uuid4())
        user = request.user
        org = user.org

        if not org:
            return Response({'error': 'User has no organization'}, status=400)

        task_record = TaskRecord.objects.create(
            task_type='agent_chat',
            org=org,
            payload={'message': message[:500], 'session_id': session_id},
        )

        from apps.tasks.tasks import run_agent_task
        run_agent_task.apply_async(
            kwargs={
                'message': message,
                'session_id': session_id,
                'user_id': str(user.id),
                'org_id': str(org.id),
                'task_record_id': str(task_record.id),
            },
            queue='default',
        )

        return Response(
            {'task_id': str(task_record.id), 'session_id': session_id},
            status=202,
        )


class ClearSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, session_id):
        ShortTermMemory.clear(session_id)
        return Response({'cleared': True})

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.rbac.services import RBACService


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        permissions = RBACService.get_user_permissions(user)
        return Response({
            'id': str(user.id),
            'email': user.email,
            'display_name': user.display_name,
            'org': {'id': str(user.org.id), 'name': user.org.name} if user.org else None,
            'permissions': list(permissions),
            'roles': [r.role.name for r in user.roles.all()],
        })

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Permission, Role, RolePermission, UserRole
from .services import RBACService
from .permissions import HasRBACPermission
from .permissions_registry import Perm, permission_registry


class PermissionsView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("rbac").view]

    def get(self, request):
        perms = Permission.objects.all().values('code', 'description')
        return Response(list(perms))


class RolesView(APIView):
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("rbac").view]

    def get(self, request):
        roles = Role.objects.filter(org=request.user.org).prefetch_related('permissions')
        return Response([
            {
                'id': str(r.id),
                'name': r.name,
                'description': r.description,
                'permissions': list(r.permissions.values_list('code', flat=True)),
            }
            for r in roles
        ])


class MyPermissionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'permissions': list(RBACService.get_user_permissions(request.user)),
        })


class TogglePermissionView(APIView):
    """Grant or revoke a permission for a role. Returns new state."""
    permission_classes = [IsAuthenticated, HasRBACPermission]
    required_permission = permission_registry[Perm("rbac").edit]

    def post(self, request, role_id):
        permission_code = request.data.get('permission_code')
        if not permission_code:
            return Response({'error': 'permission_code required'}, status=400)

        try:
            role = Role.objects.get(id=role_id, org=request.user.org)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=404)

        try:
            perm = Permission.objects.get(code=permission_code)
        except Permission.DoesNotExist:
            return Response({'error': f'Permission {permission_code!r} not found'}, status=404)

        existing = RolePermission.objects.filter(role=role, permission=perm).first()
        if existing:
            existing.delete()
            granted = False
        else:
            RolePermission.objects.create(role=role, permission=perm)
            granted = True

        for user_role in role.user_assignments.select_related('user').all():
            RBACService.invalidate_cache(user_role.user)

        return Response({
            'granted': granted,
            'permission': permission_code,
            'role': role.name,
            'affected_users': role.user_assignments.count(),
        })

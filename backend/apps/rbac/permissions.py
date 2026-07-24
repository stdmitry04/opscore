from rest_framework.permissions import BasePermission, SAFE_METHODS
from .services import RBACService


class HasRBACPermission(BasePermission):
    """
    Usage:
        permission_classes = [IsAuthenticated, HasRBACPermission]
        required_permission = permission_registry[Perm("hr.employee").view]   # read gate
        edit_permission    = permission_registry[Perm("hr.employee").edit]    # write gate (optional)

    For safe methods (GET, HEAD, OPTIONS) the view's required_permission is checked.
    For mutating methods (POST, PUT, PATCH, DELETE) edit_permission is checked when present,
    falling back to required_permission if not set.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            required = getattr(view, 'required_permission', None)
        else:
            required = getattr(view, 'edit_permission', None) or getattr(view, 'required_permission', None)
        if not required:
            return True
        return RBACService.has_permission(request.user, required)

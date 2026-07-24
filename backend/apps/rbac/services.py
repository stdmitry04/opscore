from django.core.cache import cache
from .models import UserRole
from .permissions_registry import Perm, permission_registry

CACHE_PREFIX = 'rbac:perms:'
CACHE_TTL = 300


class RBACService:
    @staticmethod
    def get_user_permissions(user) -> frozenset:
        if user.is_superuser:
            return frozenset(str(p) for p in permission_registry.all())

        cache_key = f'{CACHE_PREFIX}{user.id}'
        cached = cache.get(cache_key)
        if cached is not None:
            return frozenset(cached)

        perms = set()
        for user_role in (
            UserRole.objects.filter(user=user)
            .select_related('role')
            .prefetch_related('role__permissions')
        ):
            for perm in user_role.role.permissions.all():
                perms.add(perm.code)

        cache.set(cache_key, list(perms), CACHE_TTL)
        return frozenset(perms)

    @staticmethod
    def has_permission(user, perm: 'Perm | str') -> bool:
        if isinstance(perm, str):
            perm = Perm(perm)
        if perm not in permission_registry:
            raise ValueError(
                f"Unknown permission: {perm!r}. "
                f"Add it to permission_registry in permissions_registry.py."
            )
        return str(perm) in RBACService.get_user_permissions(user)

    @staticmethod
    def invalidate_cache(user):
        cache.delete(f'{CACHE_PREFIX}{user.id}')

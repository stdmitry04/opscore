from dataclasses import dataclass


@dataclass(frozen=True)
class PermMeta:
    description: str = ''
    sensitive: bool = False
    category: str = ''


class Perm:
    def __init__(self, code: str, *, description: str = '', sensitive: bool = False, category: str = ''):
        self._code = code
        self.meta = PermMeta(description=description, sensitive=sensitive, category=category)

    @property
    def view(self) -> 'Perm':
        return Perm(
            f"{self._code}.view",
            description=f"View {self.meta.description}",
            sensitive=self.meta.sensitive,
            category=self.meta.category,
        )

    @property
    def edit(self) -> 'Perm':
        return Perm(
            f"{self._code}.edit",
            description=f"Edit {self.meta.description}",
            sensitive=self.meta.sensitive,
            category=self.meta.category,
        )

    def __str__(self) -> str:
        return self._code

    def __repr__(self) -> str:
        return f"Perm({self._code!r})"

    def __hash__(self) -> int:
        return hash(self._code)

    def __eq__(self, other) -> bool:
        if isinstance(other, Perm):
            return self._code == other._code
        if isinstance(other, str):
            return self._code == other
        return NotImplemented


class PermRegistry:
    def __init__(self, perms: list[Perm]):
        self._registry: dict[str, Perm] = {}
        for base in perms:
            for variant in (base.view, base.edit):
                self._registry[str(variant)] = variant

    def __getitem__(self, perm: 'Perm | str') -> Perm:
        code = str(perm)
        if code not in self._registry:
            raise KeyError(
                f"Permission {code!r} is not registered. "
                f"Add a base Perm to permission_registry in permissions_registry.py."
            )
        return self._registry[code]

    def __contains__(self, perm: 'Perm | str') -> bool:
        return str(perm) in self._registry

    def all(self) -> list[Perm]:
        return list(self._registry.values())


permission_registry = PermRegistry([
    Perm("hr.employee",             description="employees",             category="hr"),
    Perm("hr.employee.salary",      description="employee salary",       category="hr", sensitive=True),
    Perm("hr.job",                  description="job postings",          category="hr"),
    Perm("hr.document",             description="HR documents",          category="hr"),
    Perm("analytics",               description="workforce analytics",   category="analytics"),
    Perm("analytics.salary_report", description="salary reports",        category="analytics", sensitive=True),
    Perm("agent.chat",              description="AI assistant",          category="agent"),
    Perm("agent.tool_calls",        description="agent tool calls",      category="agent"),
    Perm("tasks",                   description="task queue",            category="tasks"),
    Perm("rbac",                    description="roles and permissions", category="rbac"),
])


def sync_permissions():
    """Materialize permission_registry into the Permission table. Convergent — safe to run repeatedly."""
    from .models import Permission
    registered = {str(p): p for p in permission_registry.all()}
    existing = set(Permission.objects.values_list('code', flat=True))

    to_create = [
        Permission(code=code, description=perm.meta.description)
        for code, perm in registered.items()
        if code not in existing
    ]
    if to_create:
        Permission.objects.bulk_create(to_create, ignore_conflicts=True)

    stale = existing - registered.keys()
    if stale:
        Permission.objects.filter(code__in=stale).delete()

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.models import Organization, User
from apps.rbac.models import Permission, Role, RolePermission, UserRole
from apps.rbac.permissions_registry import sync_permissions, permission_registry


@pytest.fixture
def org(db):
    sync_permissions()
    return Organization.objects.create(name='Test Corp', slug='test-corp')


def _make_user(org, email, perm_codes, role_name):
    user = User.objects.create_user(email=email, password='pass123', org=org)
    perm_map = {p.code: p for p in Permission.objects.all()}
    role, _ = Role.objects.get_or_create(org=org, name=role_name, defaults={'description': ''})
    for code in perm_codes:
        if code in perm_map:
            RolePermission.objects.get_or_create(role=role, permission=perm_map[code])
    UserRole.objects.get_or_create(user=user, role=role)
    return user


@pytest.fixture
def admin_user(db, org):
    all_codes = list(permission_registry._registry.keys())
    user = _make_user(org, 'admin@test.com', all_codes, 'Admin')
    user.is_staff = True
    user.save()
    return user


@pytest.fixture
def hr_user(db, org):
    return _make_user(org, 'hr@test.com', [
        'hr.employee.view', 'hr.employee.edit',
        'hr.employee.salary.view',
        'hr.job.view', 'hr.job.edit',
        'hr.document.view', 'hr.document.edit',
        'analytics.view', 'agent.chat.view', 'agent.tool_calls.view',
        'tasks.view', 'rbac.view',
    ], 'HR Manager')


@pytest.fixture
def finance_user(db, org):
    return _make_user(org, 'finance@test.com', [
        'hr.employee.view', 'hr.employee.salary.view',
        'analytics.view', 'analytics.salary_report.view',
        'agent.chat.view', 'tasks.view',
    ], 'Finance')


@pytest.fixture
def viewer_user(db, org):
    return _make_user(org, 'viewer@test.com', [
        'hr.employee.view', 'hr.job.view', 'hr.document.view',
        'analytics.view', 'agent.chat.view',
    ], 'Viewer')


@pytest.fixture
def no_perm_user(db, org):
    return _make_user(org, 'noperm@test.com', [], 'NoPerms')


def _make_client(user) -> APIClient:
    token = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
    return client


@pytest.fixture
def admin_client(admin_user):
    return _make_client(admin_user)


@pytest.fixture
def hr_client(hr_user):
    return _make_client(hr_user)


@pytest.fixture
def finance_client(finance_user):
    return _make_client(finance_user)


@pytest.fixture
def viewer_client(viewer_user):
    return _make_client(viewer_user)


@pytest.fixture
def no_perm_client(no_perm_user):
    return _make_client(no_perm_user)


@pytest.fixture
def anon_client():
    return APIClient()

import pytest

pytestmark = pytest.mark.django_db


# ── Permissions list ──────────────────────────────────────────────────────────

class TestPermissionsEndpoint:
    def test_hr_can_list_permissions(self, hr_client):
        r = hr_client.get('/api/rbac/permissions/')
        assert r.status_code == 200
        assert len(r.data) == 20  # 10 base perms × 2 leaves

    def test_permissions_have_expected_fields(self, hr_client):
        r = hr_client.get('/api/rbac/permissions/')
        assert r.status_code == 200
        first = r.data[0]
        assert 'code' in first
        assert 'description' in first

    def test_viewer_cannot_list_permissions(self, viewer_client):
        r = viewer_client.get('/api/rbac/permissions/')
        assert r.status_code == 403

    def test_no_perm_denied(self, no_perm_client):
        r = no_perm_client.get('/api/rbac/permissions/')
        assert r.status_code == 403

    def test_unauthenticated_denied(self, anon_client):
        r = anon_client.get('/api/rbac/permissions/')
        assert r.status_code == 401


# ── Roles list ────────────────────────────────────────────────────────────────

class TestRolesEndpoint:
    def test_hr_can_list_roles(self, hr_client, hr_user):
        r = hr_client.get('/api/rbac/roles/')
        assert r.status_code == 200
        assert isinstance(r.data, list)

    def test_roles_include_permission_list(self, hr_client, hr_user):
        r = hr_client.get('/api/rbac/roles/')
        assert len(r.data) > 0
        role = next(role for role in r.data if role['name'] == 'HR Manager')
        assert 'permissions' in role
        assert 'hr.employee.view' in role['permissions']

    def test_viewer_cannot_list_roles(self, viewer_client):
        r = viewer_client.get('/api/rbac/roles/')
        assert r.status_code == 403


# ── My permissions ────────────────────────────────────────────────────────────

class TestMyPermissionsEndpoint:
    def test_returns_user_permissions(self, hr_client):
        r = hr_client.get('/api/rbac/me/')
        assert r.status_code == 200
        assert 'permissions' in r.data
        assert 'hr.employee.view' in r.data['permissions']

    def test_viewer_permissions_scoped_correctly(self, viewer_client):
        r = viewer_client.get('/api/rbac/me/')
        perms = r.data['permissions']
        assert 'hr.employee.view' in perms
        assert 'hr.employee.edit' not in perms
        assert 'hr.employee.salary.view' not in perms

    def test_unauthenticated_denied(self, anon_client):
        r = anon_client.get('/api/rbac/me/')
        assert r.status_code == 401


# ── Toggle permission ─────────────────────────────────────────────────────────

class TestTogglePermission:
    def test_admin_can_toggle_permission(self, admin_client, viewer_user, org):
        from apps.rbac.models import Role
        viewer_role = Role.objects.get(org=org, name='Viewer')
        r = admin_client.post(
            f'/api/rbac/roles/{viewer_role.id}/toggle/',
            {'permission_code': 'hr.document.edit'},
        )
        assert r.status_code == 200
        assert 'granted' in r.data
        assert r.data['permission'] == 'hr.document.edit'

    def test_toggle_is_idempotent_toggle(self, admin_client, viewer_user, org):
        from apps.rbac.models import Role
        viewer_role = Role.objects.get(org=org, name='Viewer')
        # First toggle: grant
        r1 = admin_client.post(
            f'/api/rbac/roles/{viewer_role.id}/toggle/',
            {'permission_code': 'hr.document.edit'},
        )
        assert r1.data['granted'] is True
        # Second toggle: revoke
        r2 = admin_client.post(
            f'/api/rbac/roles/{viewer_role.id}/toggle/',
            {'permission_code': 'hr.document.edit'},
        )
        assert r2.data['granted'] is False

    def test_toggle_without_permission_code_returns_400(self, admin_client, org, admin_user):
        from apps.rbac.models import Role
        role = Role.objects.get(org=org, name='Admin')
        r = admin_client.post(f'/api/rbac/roles/{role.id}/toggle/', {})
        assert r.status_code == 400

    def test_toggle_nonexistent_role_returns_404(self, admin_client):
        r = admin_client.post(
            '/api/rbac/roles/00000000-0000-0000-0000-000000000000/toggle/',
            {'permission_code': 'hr.employee.view'},
        )
        assert r.status_code == 404

    def test_toggle_invalid_perm_code_returns_404(self, admin_client, org, admin_user):
        from apps.rbac.models import Role
        role = Role.objects.get(org=org, name='Admin')
        r = admin_client.post(
            f'/api/rbac/roles/{role.id}/toggle/',
            {'permission_code': 'nonexistent.perm'},
        )
        assert r.status_code == 404

    def test_hr_cannot_toggle_permissions(self, hr_client, org, hr_user):
        from apps.rbac.models import Role
        hr_role = Role.objects.get(org=org, name='HR Manager')
        r = hr_client.post(
            f'/api/rbac/roles/{hr_role.id}/toggle/',
            {'permission_code': 'hr.document.edit'},
        )
        assert r.status_code == 403

    def test_toggle_invalidates_permission_cache(self, admin_client, viewer_client, viewer_user, org):
        from apps.rbac.models import Role
        from apps.rbac.services import RBACService
        from apps.rbac.permissions_registry import permission_registry, Perm

        viewer_role = Role.objects.get(org=org, name='Viewer')
        doc_edit = permission_registry[Perm("hr.document").edit]

        # Before toggle: viewer cannot edit documents
        assert not RBACService.has_permission(viewer_user, doc_edit)

        # Grant the permission
        admin_client.post(
            f'/api/rbac/roles/{viewer_role.id}/toggle/',
            {'permission_code': 'hr.document.edit'},
        )

        # After toggle: viewer CAN edit documents
        assert RBACService.has_permission(viewer_user, doc_edit)

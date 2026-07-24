import pytest

pytestmark = pytest.mark.django_db


class TestHealthEndpoint:
    def test_health_returns_ok(self, anon_client):
        r = anon_client.get('/api/health/')
        assert r.status_code == 200
        assert r.json()['status'] == 'ok'


class TestTokenObtain:
    def test_valid_credentials_return_tokens(self, anon_client, hr_user):
        r = anon_client.post('/api/auth/token/', {
            'email': 'hr@test.com', 'password': 'pass123'
        })
        assert r.status_code == 200
        assert 'access' in r.data
        assert 'refresh' in r.data

    def test_wrong_password_rejected(self, anon_client, hr_user):
        r = anon_client.post('/api/auth/token/', {
            'email': 'hr@test.com', 'password': 'wrong'
        })
        assert r.status_code == 401

    def test_nonexistent_user_rejected(self, anon_client, org):
        r = anon_client.post('/api/auth/token/', {
            'email': 'nobody@test.com', 'password': 'pass'
        })
        assert r.status_code == 401

    def test_refresh_token_works(self, anon_client, hr_user):
        r = anon_client.post('/api/auth/token/', {
            'email': 'hr@test.com', 'password': 'pass123'
        })
        refresh = r.data['refresh']
        r2 = anon_client.post('/api/auth/token/refresh/', {'refresh': refresh})
        assert r2.status_code == 200
        assert 'access' in r2.data


class TestMeEndpoint:
    def test_authenticated_returns_user_info(self, hr_client, hr_user):
        r = hr_client.get('/api/auth/me/')
        assert r.status_code == 200
        assert r.data['email'] == 'hr@test.com'

    def test_includes_permissions_list(self, hr_client):
        r = hr_client.get('/api/auth/me/')
        assert 'permissions' in r.data
        assert 'hr.employee.view' in r.data['permissions']

    def test_includes_roles_list(self, hr_client):
        r = hr_client.get('/api/auth/me/')
        assert 'roles' in r.data
        assert 'HR Manager' in r.data['roles']

    def test_includes_org_info(self, hr_client):
        r = hr_client.get('/api/auth/me/')
        assert r.data['org']['name'] == 'Test Corp'

    def test_unauthenticated_returns_401(self, anon_client):
        r = anon_client.get('/api/auth/me/')
        assert r.status_code == 401

    def test_permissions_scoped_to_role(self, viewer_client):
        r = viewer_client.get('/api/auth/me/')
        perms = r.data['permissions']
        assert 'hr.employee.view' in perms
        assert 'hr.employee.salary.view' not in perms
        assert 'hr.document.edit' not in perms

    def test_admin_has_all_permissions(self, admin_client):
        r = admin_client.get('/api/auth/me/')
        perms = r.data['permissions']
        assert 'hr.employee.view' in perms
        assert 'hr.employee.salary.view' in perms
        assert 'rbac.edit' in perms

import pytest
from unittest.mock import patch
from datetime import date

from apps.hr.models import Employee, Job, Document

pytestmark = pytest.mark.django_db


@pytest.fixture
def employee(org):
    return Employee.objects.create(
        org=org, first_name='Jane', last_name='Smith',
        email='jane.smith@test.com', title='Engineer',
        department='Engineering', hire_date=date(2022, 1, 15),
        salary=120000, status='active',
    )


@pytest.fixture
def job(org):
    return Job.objects.create(
        org=org, title='Senior Engineer', department='Engineering',
        description='Lead backend systems', requirements='5+ years Python',
        salary_min=120000, salary_max=160000, status='open',
    )


@pytest.fixture
def document(org):
    return Document.objects.create(
        org=org, name='Remote Work Policy',
        content='All employees may work remotely after 90 days.',
        doc_type='policy',
    )


# ── Employee list ─────────────────────────────────────────────────────────────

class TestEmployeeList:
    def test_viewer_can_list(self, viewer_client, employee):
        r = viewer_client.get('/api/hr/employees/')
        assert r.status_code == 200

    def test_list_salary_not_exposed(self, viewer_client, employee):
        r = viewer_client.get('/api/hr/employees/')
        results = r.data.get('results', r.data)
        if isinstance(results, list) and results:
            assert 'salary' not in results[0]

    def test_unauthenticated_denied(self, anon_client):
        r = anon_client.get('/api/hr/employees/')
        assert r.status_code == 401

    def test_no_perm_user_denied(self, no_perm_client):
        r = no_perm_client.get('/api/hr/employees/')
        assert r.status_code == 403

    def test_cross_org_isolation(self, viewer_client, employee):
        from apps.core.models import Organization, User
        from conftest import _make_client, _make_user
        from apps.rbac.permissions_registry import sync_permissions
        sync_permissions()
        other_org = Organization.objects.create(name='Other Corp', slug='other-corp')
        other_user = _make_user(other_org, 'other@other.com', ['hr.employee.view'], 'Viewer')
        other_client = _make_client(other_user)
        r = other_client.get('/api/hr/employees/')
        assert r.status_code == 200
        # other org's user cannot see test corp's employees
        results = r.data.get('results', r.data)
        if isinstance(results, list):
            assert all(str(employee.id) not in str(e.get('id', '')) for e in results)


# ── Employee detail ───────────────────────────────────────────────────────────

class TestEmployeeDetail:
    def test_viewer_can_retrieve(self, viewer_client, employee):
        r = viewer_client.get(f'/api/hr/employees/{employee.id}/')
        assert r.status_code == 200
        assert r.data['first_name'] == 'Jane'

    def test_salary_visible_to_hr(self, hr_client, employee):
        r = hr_client.get(f'/api/hr/employees/{employee.id}/')
        assert r.status_code == 200
        assert float(r.data['salary']) == 120000.0

    def test_nonexistent_employee_returns_404(self, viewer_client):
        r = viewer_client.get('/api/hr/employees/00000000-0000-0000-0000-000000000000/')
        assert r.status_code == 404

    def test_no_perm_denied(self, no_perm_client, employee):
        r = no_perm_client.get(f'/api/hr/employees/{employee.id}/')
        assert r.status_code == 403


# ── Employee mutations ────────────────────────────────────────────────────────

class TestEmployeeMutations:
    def test_hr_can_create_employee(self, hr_client, org):
        r = hr_client.post('/api/hr/employees/', {
            'first_name': 'Bob', 'last_name': 'Jones',
            'email': 'bob.jones@test.com', 'title': 'Analyst',
            'department': 'Finance', 'hire_date': '2024-01-01',
            'status': 'active', 'org': str(org.id),
        })
        assert r.status_code == 201

    def test_viewer_cannot_create_employee(self, viewer_client, org):
        r = viewer_client.post('/api/hr/employees/', {
            'first_name': 'Bob', 'last_name': 'Jones',
            'email': 'bob.jones2@test.com', 'title': 'Analyst',
            'department': 'Finance', 'hire_date': '2024-01-01',
            'status': 'active', 'org': str(org.id),
        })
        assert r.status_code == 403

    def test_hr_can_update_employee(self, hr_client, employee):
        r = hr_client.patch(f'/api/hr/employees/{employee.id}/', {'title': 'Staff Engineer'})
        assert r.status_code == 200
        assert r.data['title'] == 'Staff Engineer'

    def test_viewer_cannot_update_employee(self, viewer_client, employee):
        r = viewer_client.patch(f'/api/hr/employees/{employee.id}/', {'title': 'Staff Engineer'})
        assert r.status_code == 403


# ── Salary report ─────────────────────────────────────────────────────────────

class TestSalaryReport:
    def test_hr_can_access_salary_report(self, hr_client, employee):
        r = hr_client.get('/api/hr/employees/salary_report/')
        assert r.status_code == 200

    def test_finance_can_access_salary_report(self, finance_client, employee):
        r = finance_client.get('/api/hr/employees/salary_report/')
        assert r.status_code == 200

    def test_viewer_denied_salary_report(self, viewer_client, employee):
        r = viewer_client.get('/api/hr/employees/salary_report/')
        assert r.status_code == 403

    def test_no_perm_denied_salary_report(self, no_perm_client):
        r = no_perm_client.get('/api/hr/employees/salary_report/')
        assert r.status_code == 403


# ── Jobs ──────────────────────────────────────────────────────────────────────

class TestJobEndpoints:
    def test_viewer_can_list_jobs(self, viewer_client, job):
        r = viewer_client.get('/api/hr/jobs/')
        assert r.status_code == 200

    def test_hr_can_create_job(self, hr_client, org):
        r = hr_client.post('/api/hr/jobs/', {
            'title': 'Data Engineer', 'department': 'Engineering',
            'description': 'Build our data pipelines',
            'requirements': '3+ years SQL and Python',
            'status': 'open', 'org': str(org.id),
        })
        assert r.status_code == 201

    def test_viewer_cannot_create_job(self, viewer_client, org):
        r = viewer_client.post('/api/hr/jobs/', {
            'title': 'Data Engineer', 'department': 'Engineering',
            'description': 'Build our data pipelines',
            'requirements': '3+ years SQL',
            'status': 'open', 'org': str(org.id),
        })
        assert r.status_code == 403

    def test_no_perm_cannot_list_jobs(self, no_perm_client):
        r = no_perm_client.get('/api/hr/jobs/')
        assert r.status_code == 403

    def test_hr_can_delete_job(self, hr_client, job):
        r = hr_client.delete(f'/api/hr/jobs/{job.id}/')
        assert r.status_code == 204

    def test_viewer_cannot_delete_job(self, viewer_client, job):
        r = viewer_client.delete(f'/api/hr/jobs/{job.id}/')
        assert r.status_code == 403


# ── Documents ─────────────────────────────────────────────────────────────────

class TestDocumentEndpoints:
    def test_viewer_can_list_documents(self, viewer_client, document):
        r = viewer_client.get('/api/hr/documents/')
        assert r.status_code == 200

    def test_no_perm_denied_document_list(self, no_perm_client):
        r = no_perm_client.get('/api/hr/documents/')
        assert r.status_code == 403

    def test_hr_can_upload_document(self, hr_client, org):
        with patch('apps.tasks.tasks.embed_document.apply_async'):
            r = hr_client.post('/api/hr/documents/', {
                'name': 'Benefits Guide', 'doc_type': 'handbook',
                'content': 'We offer health insurance and 401k.',
            }, format='multipart')
        assert r.status_code == 202
        assert 'task_id' in r.data
        assert 'document' in r.data

    def test_viewer_cannot_upload_document(self, viewer_client):
        r = viewer_client.post('/api/hr/documents/', {
            'name': 'Benefits Guide', 'doc_type': 'handbook',
        }, format='multipart')
        assert r.status_code == 403

    def test_document_search_returns_results(self, hr_client, document):
        with patch('apps.agent.rag.RAGService.search', return_value=[]):
            r = hr_client.get('/api/hr/documents/search/', {'q': 'remote work'})
        assert r.status_code == 200
        assert 'results' in r.data

    def test_document_search_requires_q_param(self, hr_client):
        r = hr_client.get('/api/hr/documents/search/')
        assert r.status_code == 400


# ── Analytics ─────────────────────────────────────────────────────────────────

class TestAnalyticsEndpoint:
    def test_viewer_can_access_analytics(self, viewer_client, employee):
        r = viewer_client.get('/api/hr/analytics/')
        assert r.status_code == 200
        assert 'headcount' in r.data
        assert 'department_breakdown' in r.data
        assert 'avg_salary' in r.data
        assert 'open_jobs' in r.data

    def test_headcount_reflects_employee_status(self, viewer_client, employee):
        r = viewer_client.get('/api/hr/analytics/')
        assert r.data['headcount']['active'] >= 1
        assert r.data['headcount']['total'] >= 1

    def test_no_perm_denied_analytics(self, no_perm_client):
        r = no_perm_client.get('/api/hr/analytics/')
        assert r.status_code == 403

    def test_unauthenticated_denied_analytics(self, anon_client):
        r = anon_client.get('/api/hr/analytics/')
        assert r.status_code == 401
